import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import sqlitecloud
import re
from model_api_utils import HuggingFaceAPIChain, resize_image, bytes_to_base64, base64_to_bytes, process_file_from_json
from chat_history_utils import create_new_chat, save_chat, load_chat, list_chats, clear_chat
from database_utils import update_user_params
from folder_manager_utils import load_folders, add_folder, remove_folder, add_chat_to_folder, remove_chat_from_folder
import time

# Установка параметров страницы
st.set_page_config(
    page_title="Чат-бот",
    page_icon="static/img/robot.png",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items=None
)

# Настройка yaml и sqlite базы данных для работы со stauth
with open('static/yaml/config.yaml', encoding='utf-8') as file:
    config = yaml.load(file, Loader=SafeLoader)

database_connection = sqlitecloud.connect("sqlitecloud://cwhn6fmohk.g6.sqlite.cloud:8860/streamlit-app?apikey=J9RVuB0yk0yBtz2rcqar5m9GmdftlBq7ce03ryZYtH8")
database_connection.execute("USE DATABASE streamlit-app")
database_connection.row_factory = sqlitecloud.Row
cursor = database_connection.execute("SELECT * FROM users")

rows = cursor.fetchall()
data = [dict(row) for row in rows]

data_dict = {}
for user in data:
    data_dict[user['username']] = {
        'email': user['email'],
        'failed_login_attempts': user['failed_login_attempts'],
        'first_name': user['first_name'],
        'last_name': user['last_name'],
        'logged_in': user['logged_in'],
        'password': user['password'],
        'password_hint': user['password_hint'],
        'roles': user['roles'],
        'theme_button': user.get('theme_button'),
        'current_chat': user.get('current_chat'),
        'selected_model': user.get('selected_model')
    }

# Преобразование data_dict в users_dict для корректной работы со StreamlitAuthenticator
users_dict = {}
users_dict['usernames'] = data_dict 

authenticator = stauth.Authenticate(
    users_dict,
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# URL для HuggingFace API
MISTRAL_URL = st.secrets["API"]["MISTRAL_URL"]
XLSUM_URL = st.secrets["API"]["XLSUM_URL"]
FLUX_URL = st.secrets["API"]["FLUX_URL"]
API_TOKEN = st.secrets["API"]["TOKEN"]
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

model_options = {
    "Mistral": MISTRAL_URL,
    "XLSum": XLSUM_URL,
    "Flux": FLUX_URL
}

# Функции подключения css и инициализации session_state
def load_css():
    with open("static/css/styles.css", "r") as file:
        css = f"<style>{file.read()}</style>"
        st.markdown(css, unsafe_allow_html=True)
        
def initialize_session_state(username):
    user_data = data_dict.get(username, {})

    if 'messages' not in st.session_state:
        st.session_state['messages'] = []

    if 'theme_button' not in st.session_state and user_data.get('theme_button') != "NULL":
        st.session_state['theme_button'] = user_data['theme_button']

    if 'selected_model' not in st.session_state and user_data.get('selected_model') != "NULL":
        st.session_state['selected_model'] = user_data['selected_model']

    if 'current_chat' not in st.session_state and user_data.get('current_chat') != "NULL":
        st.session_state['current_chat'] = user_data['current_chat']
        st.session_state['messages'] = load_chat(user_data['current_chat'])
    
    else:
        if 'theme_button' not in st.session_state:
            st.session_state['theme_button'] = 'light'

        if 'selected_model' not in st.session_state:
            st.session_state['selected_model'] = 'Mistral'

        if 'current_chat' not in st.session_state:
            st.session_state['current_chat'] = None

load_css()
chat_list = list_chats()
folders = load_folders()

# Отображение интерфейса в случае успешной авторизации
if st.session_state['authentication_status']:
    initialize_session_state(st.session_state["username"])
    update_user_params(st.session_state["username"], logged_in_status=1)

    # Сайдбар меню
    st.logo("static/img/robot.png", size="large")
    with st.sidebar:
        with st.container(key="profile"):
            with st.popover("Настройки"):
                # Основная информация о пользователе
                st.write(f'**Имя пользователя:** {st.session_state["username"]}')
                if st.session_state.get("roles") == "NULL":
                    st.write('**Роли:** не назначены.')
                else:
                    st.write(f'**Роли:** {st.session_state["roles"]}.')

                # Изменение модели
                model_radio = st.radio(
                    "**LLM модель:**",
                    options=list(model_options.keys()),
                    index=list(model_options.keys()).index(st.session_state['selected_model']),
                    format_func=lambda x: x,
                    horizontal=True
                )
                API_URL = model_options[model_radio]

                if model_radio != st.session_state['selected_model']:
                    st.session_state['selected_model'] = model_radio
                    update_user_params(st.session_state["username"], selected_model=st.session_state['selected_model'])
                    st.rerun()

                # Изменение темы
                theme = st.radio(
                    "**Тема:**", 
                    options=["Светлая", "Темная"],
                    index=0 if st.session_state['theme_button'] == 'light' else 1, 
                    horizontal=True
                )

                if theme == "Темная" and st.session_state['theme_button'] != 'dark':
                    selected_theme = 'dark'
                    st.session_state['theme_button'] = selected_theme
                    st._config.set_option('theme.base', selected_theme)
                    update_user_params(st.session_state["username"], theme_button=st.session_state['theme_button'])
                    st.rerun()
                
                if theme == "Светлая" and st.session_state['theme_button'] != 'light':
                    selected_theme = 'light'
                    st.session_state['theme_button'] = selected_theme
                    st._config.set_option('theme.base', selected_theme)
                    update_user_params(st.session_state["username"], theme_button=st.session_state['theme_button'])
                    st.rerun()

                # Выход с приложения
                st.session_state['last_user'] = st.session_state['username']
                authenticator.logout("Выйти")
                # Изменение статуса входа пользователя на False в случае выхода
                if st.session_state['username'] == None:
                    update_user_params(st.session_state['last_user'], logged_in_status=0)

        # Поиск чата
        with st.container(key="search_query"):
            search_query = st.text_area("Поиск по содержимому чатов", key="chat_search", placeholder="Поиск чата", label_visibility="hidden", height=68)
            st.session_state['filtered_chats'] = []

            filtered_chats_placeholder = st.container(key="filtered_chats")
            no_chats_founded = st.container(key="no_chats_founded")

            if not "last_search_query" in st.session_state:
                st.session_state["last_search_query"] = search_query
            
            if st.session_state["last_search_query"] != search_query:
                st.session_state["last_search_query"] = search_query
                filtered_chats_placeholder.empty()
                st.rerun()

            if search_query:
                for chat in chat_list:
                    chat_messages = load_chat(chat)
                    if any(search_query.lower() in message["content"].lower() for message in chat_messages if "content" in message):
                        st.session_state['filtered_chats'].append(chat)

                if st.session_state['filtered_chats']:
                    with filtered_chats_placeholder:
                        with st.popover("Результаты поиска"):
                            for idx, chat in enumerate(st.session_state['filtered_chats']):
                                is_current_chat = st.session_state['current_chat'] == chat
                                chat_content = load_chat(chat)[0]['content']

                                match = re.match(r'([^.!?]*[.!?])', chat_content)
                                if match:
                                    first_sentence = match.group(0).strip()
                                else:
                                    first_sentence = chat_content[:75]
                                    
                                button = st.button(
                                    first_sentence.strip(),
                                    key=f"finded_chat-{idx}", 
                                    type="secondary",
                                    disabled=is_current_chat
                                )
                                if button and not is_current_chat:
                                    st.session_state['current_chat'] = chat
                                    st.session_state['messages'] = load_chat(chat)
                                    update_user_params(st.session_state["username"], current_chat=st.session_state['current_chat'])
                                    st.markdown(
                                        """
                                        <div class="spinner-container">
                                            <div class="spinner"></div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
                                    time.sleep(1)
                                    st.markdown("<meta http-equiv='refresh' content='0'>", unsafe_allow_html=True)
                else:
                    with filtered_chats_placeholder:
                        st.write("Не найдено чатов по вашему запросу")

        # Менеджер папок
        with st.container(key="folder_manager"):
            with st.popover("Менеджер папок"):
                st.write("### Управление папками")

                new_folder_name = st.text_input("Название новой папки")
                if st.button("Создать папку"):
                    if new_folder_name:
                        if add_folder(folders, new_folder_name):
                            st.rerun()
                        else:
                            st.error(f"Папка '{new_folder_name}' уже существует.")

                folder_to_remove = st.selectbox("Выберите папку для удаления", [folder['folder_name'] for folder in folders] + [""])
                if st.button("Удалить папку"):
                    if folder_to_remove:
                        remove_folder(folders, folder_to_remove)
                        st.rerun()

                folder_placeholder = st.empty()
                with folder_placeholder:
                    st.write("### Существующие папки")
                    for folder in folders:
                        with st.expander(folder['folder_name']):
                            cols = st.columns([5, 1])
                            for chat in folder['chats']:
                                with cols[0]:
                                    st.button(chat['chat_name'])
                                with cols[1]:
                                    if st.button(f"❌", key=f"remove_{chat['chat_name']}"):
                                        remove_chat_from_folder(folders, folder['folder_name'], chat['chat_name'])
                                        st.rerun()

                            new_chat_selectbox = st.selectbox(
                                f"Выберите чат для добавления в {folder['folder_name']}", 
                                chat_list, 
                                key=f"{folder['folder_name']}_select", 
                            )
                            if st.button(f"Добавить чат в {folder['folder_name']}"):
                                selected_chat = new_chat_selectbox
                                if add_chat_to_folder(folders, folder['folder_name'], selected_chat):
                                    st.rerun()  
                    
        # Список всех чатов
        with st.container(key="chat-list"):
            st.subheader("Список чатов")
            if st.button("Создать новый чат", key=f"new_chat", type="primary"):
                new_chat_name = create_new_chat()
                st.session_state['current_chat'] = new_chat_name
                st.session_state['messages'] = []
                update_user_params(st.session_state["username"], current_chat=st.session_state['current_chat'])

            if chat_list:
                for idx, chat in enumerate(chat_list):
                    is_current_chat = st.session_state['current_chat'] == chat
                    button = st.button(
                        load_chat(chat)[0]['content'][:100], 
                        key=f"chat-{idx}", 
                        type="secondary",
                        disabled=is_current_chat
                    )
                    if button and not is_current_chat:
                        st.session_state.messages = []
                        st.session_state['current_chat'] = chat
                        st.session_state['messages'] = load_chat(chat)
                        update_user_params(st.session_state["username"], current_chat=st.session_state['current_chat'])
                        st.markdown(
                            """
                            <div class="spinner-container">
                                <div class="spinner"></div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        time.sleep(1)
                        st.markdown("<meta http-equiv='refresh' content='0'>", unsafe_allow_html=True)

    # Реализация чат-бот интерфейса с помощью Streamlit
    chat_placeholder = st.container()
    title_placeholder = st.empty()
    popular_prompt_placeholder = st.empty()
    interface_placeholder = st.container(key="interface")
    spinner_placeholder = st.container()
    
    if not st.session_state['current_chat']:
        st.session_state['current_chat'] = create_new_chat()
    if 'popular_prompt' not in st.session_state:
        st.session_state['popular_prompt'] = None

    # Контейнер для всего интерфейса
    with interface_placeholder:
        # Контейнер для сообщений чата
        with chat_placeholder:
            if not st.session_state['messages']:
                title_placeholder.title("Добро пожаловать!")
                with popular_prompt_placeholder.expander("Примеры популярных запросов"):
                    if st.button("Какая сегодня погода в Санкт-Петербурге?"):
                        st.session_state['popular_prompt'] = "Какая сегодня погода в Санкт-Петербурге?"
                    if st.button("Расскажи мне о языке Python."):
                        st.session_state['popular_prompt'] = "Расскажи мне о языке Python."
                    if st.button("Можешь ли ты сделать мне отчет в .xslx формате?"):
                        st.session_state['popular_prompt'] = "Можешь ли ты сделать мне отчет в .xslx формате?"

            if st.session_state['messages']:
                for message in st.session_state['messages']:
                    with st.chat_message(message["role"]):
                        if "content" in message:
                            st.markdown(message["content"])
                        if "image" in message:
                            st.image(resize_image(base64_to_bytes(message["image"]), 400))
                        if "file" in message:
                            process_file_from_json(message["file"])

        # Изменение модели
        model_selectbox = st.selectbox(
            "**LLM модель:**",
            options=list(model_options.keys()),
            index=list(model_options.keys()).index(st.session_state['selected_model']),
            format_func=lambda x: x,
            label_visibility = "hidden"
        )
        API_URL = model_options[model_selectbox]

        if model_selectbox != st.session_state['selected_model']:
            st.session_state['selected_model'] = model_selectbox
            update_user_params(st.session_state["username"], selected_model=st.session_state['selected_model'])
            st.rerun()

        # Вывод запроса пользователя на экран (выбранного популярного/введенного)
        if "popular_prompt" in st.session_state and st.session_state['popular_prompt']:
            prompt = st.session_state['popular_prompt']
            st.session_state['popular_prompt'] = None
        else:
            prompt = st.chat_input("Введите ваш запрос")

        if prompt:
            huggingface_chain = HuggingFaceAPIChain(api_url=API_URL, api_headers=HEADERS)
            
            st.session_state['messages'].append({"role": "user", "content": prompt})
            title_placeholder.empty()
            popular_prompt_placeholder.empty()

            with chat_placeholder:
                with st.chat_message("user"):
                    st.markdown(prompt)

            with spinner_placeholder:
                with st.spinner("Обработка запроса"):
                    chain_call = huggingface_chain._call({"input": prompt})
                    llm_response = chain_call["output"]
            spinner_placeholder.empty()
            
            if isinstance(llm_response, str):
                st.session_state['messages'].append({"role": "assistant", "content": llm_response})
                with chat_placeholder:
                    with st.chat_message("assistant"):
                        st.markdown(llm_response)

            if isinstance(llm_response, bytes):
                st.session_state['messages'].append({"role": "assistant", "image": bytes_to_base64(llm_response)})
                with chat_placeholder:
                    with st.chat_message("assistant"):
                        st.image(resize_image(llm_response, 200))
            
            if isinstance(llm_response, dict) and "file" in llm_response:
                file_info = llm_response["file"]
                file_type = file_info["type"]
                file_name = file_info["name"]
                file_url = file_info["file_url"]

                st.session_state['messages'].append({
                    "role": "assistant",
                    "file": {"type": file_type, "name": file_name, "file_url": file_url}
                })

    # Кнопки для работы с чатом (загрузка файлов, удаление чата)
    with st.container(key="chat-widgets"):
        uploaded_files = st.file_uploader("Загрузить файлы", type=None, accept_multiple_files=True)
        if st.session_state['messages']:
            if st.button("Удалить чат", key = "delete-chat", type="primary"):
                st.session_state['messages'].clear()
                clear_chat(st.session_state['current_chat'])
                st.rerun()

    if st.session_state['current_chat'] and st.session_state['messages'] != []:
        save_chat(st.session_state['current_chat'], st.session_state['messages'])
        chat_list = list_chats()
        st.rerun()

    if uploaded_files:
        file_names = ", ".join(uploaded_file.name for uploaded_file in uploaded_files)
        st.write("Названия файлов:", file_names)
        st.session_state.messages


# Вход и регистрация
else:
    tab1, tab2 = st.tabs(["**Вход**", "**Регистрация**"])

    with tab1:
        try:
            authenticator.login(fields={
                'Form name': 'Вход',
                'Username': 'Имя пользователя',
                'Password': 'Пароль',
                'Login': 'Войти',
                'Captcha': 'Капча'
            })

            if st.session_state["authentication_status"] == False:
                st.error('Имя пользователя/пароль введены неверно.')

        except Exception as e:
            st.error(e)

    with tab2:
        try:
            user_registered = authenticator.register_user(fields={
                'Form name': 'Регистрация',
                'Username': 'Имя пользователя',
                'Email': 'Email',
                'Password': 'Пароль',
                'Email': 'Почта',
                'Repeat password': 'Повторите пароль',
                'Register': 'Зарегистрироваться',
                'Password hint': 'Подсказка пароля',
                'Captcha': 'Капча',
                'First name': 'Имя',
                'Last name': 'Фамилия'
            }, captcha=False)

            if user_registered != (None, None, None):
                st.success("Пользователь успешно зарегистрирован.")

        except Exception as e:
            st.error(e)