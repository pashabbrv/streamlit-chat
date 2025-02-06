import sqlitecloud

database_connection = sqlitecloud.connect("sqlitecloud://cwhn6fmohk.g6.sqlite.cloud:8860/streamlit-app?apikey=J9RVuB0yk0yBtz2rcqar5m9GmdftlBq7ce03ryZYtH8")
database_connection.execute("USE DATABASE streamlit-app")
database_connection.row_factory = sqlitecloud.Row
cursor = database_connection.execute("SELECT * FROM users")

def update_user_params(username, theme_button=None, current_chat=None, selected_model=None, logged_in_status=None):
    update_query = "UPDATE users SET "
    update_values = []

    if theme_button is not None:
        update_query += "theme_button = ?, "
        update_values.append(theme_button)
    if current_chat is not None:
        update_query += "current_chat = ?, "
        update_values.append(current_chat)
    if selected_model is not None:
        update_query += "selected_model = ?, "
        update_values.append(selected_model)
    if logged_in_status is not None:
        update_query += "logged_in = ?, "
        update_values.append(logged_in_status)

    update_query = update_query.rstrip(", ") + " WHERE username = ?"
    update_values.append(username)

    cursor.execute(update_query, tuple(update_values))
    database_connection.commit()