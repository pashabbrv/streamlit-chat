from dataclasses import dataclass
from typing import Literal
import streamlit as st
import streamlit.components.v1 as components
import requests
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

st.set_page_config(
    page_title="Чат-бот LLM",
    page_icon="static/img/robot.png",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items=None
)

with open('static/yaml/config.yaml', encoding='utf-8') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

API_URL = "https://api-inference.huggingface.co/models/csebuetnlp/mT5_multilingual_XLSum"
API_TOKEN = "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"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

# Класс сообщения
@dataclass
class Message:
    origin: Literal["human", "ai"]
    message: str

# Отправляет запрос к API Hugging Face и возвращает ответ модели
def query_huggingface_api(prompt: str) -> str:
    payload = {"inputs": prompt}
    response = requests.post(API_URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        return response.json()[0]['summary_text']
    else:
        st.error(f"Ошибка API Hugging Face: {response.status_code}")
        return "Ошибка при запросе к модели."

def load_css():
    with open("static/css/styles.css", "r") as file:
        css = f"<style>{file.read()}</style>"
        st.markdown(css, unsafe_allow_html=True)

def initialize_session_state():
    if "history" not in st.session_state:
        st.session_state.history = []

def on_click_callback():
    human_prompt = st.session_state.human_prompt
    with spinner_placeholder.container():
        with st.spinner("Обработка запроса"):
            llm_response = query_huggingface_api(human_prompt)
    st.session_state.history.append(Message("human", human_prompt))
    st.session_state.history.append(Message("ai", llm_response))
    spinner_placeholder.empty()

def clear_text():
    st.session_state.human_prompt = ""

load_css()
initialize_session_state()

# Сайдбар меню
st.logo("static/img/robot.png", size="large")
with st.sidebar:
        if st.session_state['authentication_status']:
            with st.container(key="login-options"):
                st.write(f'**Добро пожаловать, {st.session_state["name"]}!**')
                st.write(f'Роли: {", ".join(st.session_state["roles"])}.')
                authenticator.logout("Выйти")

            with st.container(key="chat-list"):
                st.subheader("Список чатов")
                chat_list = ["Чат 1", "Чат 2", "Чат 3", "Расскажи мне про город Санкт-Петербург."]
                for chat in chat_list:
                    st.markdown(f'<p>{chat}</p>', unsafe_allow_html=True)
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
                    authenticator.register_user(fields={
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
                    })
                except Exception as e:
                    st.error(e)

# Реализация чат-бот интерфейса с помощью Streamlit
st.title("LLM бот")
chat_placeholder = st.container()
spinner_placeholder = st.empty()
prompt_placeholder = st.form("chat-form")
credit_card_placeholder = st.empty()

with chat_placeholder:
    st.markdown("""
    <div class="chat-row">
        <img class="chat-icon" src="app/static/img/ai_icon.png">
        <div class="chat-bubble ai-bubble">
            Привет! Чем могу помочь?
        </div>
    </div>
    """, unsafe_allow_html=True)
        
    for chat in st.session_state.history:
        div = f"""
        <div class="chat-row 
            {'' if chat.origin == 'ai' else 'row-reverse'}">
            <img class="chat-icon" src="app/static/img/{
                'ai_icon.png' if chat.origin == 'ai' 
                            else 'user_icon.png'}">
            <div class="chat-bubble
            {'ai-bubble' if chat.origin == 'ai' else 'human-bubble'}">
                {chat.message}
            </div>
        </div>
        """
        st.markdown(div, unsafe_allow_html=True)
    
    for _ in range(3):
        st.markdown("")

with prompt_placeholder:
    st.markdown("""<h3>Введите ваш запрос:</h3>""", unsafe_allow_html=True)
    
    st.text_area(
        "Чат",
        value="",
        label_visibility="collapsed",
        key="human_prompt",
        height=100
    )
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col2:
        st.form_submit_button("Стереть", on_click=clear_text, use_container_width=True)
    
    with col3:
        st.form_submit_button(
            "Отправить", 
            type="primary", 
            on_click=on_click_callback,
            use_container_width=True
        )


credit_card_placeholder.caption(f"""
Debug: 
{[msg.message for msg in st.session_state.history]}
""")

components.html(
    """
    <script>
   
    document.addEventListener('DOMContentLoaded', function() {
        const textareas = window.parent.document.querySelectorAll('.stTextArea textarea');
        textareas.forEach(textarea => {
            textarea.setAttribute('placeholder', 'Место для текста');
        });
    });
                    
    </script>
    """,
    height=0,
    width=0
)
