import json
from datetime import datetime
import os

CHAT_DIRECTORY = "chat_list"

def get_timestamp():
    return datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

def list_chats():
    return [f.replace(".json", "") for f in os.listdir(CHAT_DIRECTORY) if f.endswith(".json")]

def load_chat(chat_id):
    file_path = os.path.join(CHAT_DIRECTORY, f"{chat_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_chat(chat_id, messages):
    file_path = os.path.join(CHAT_DIRECTORY, f"{chat_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

def create_new_chat():
    new_chat_id = get_timestamp()
    return new_chat_id

def clear_chat(chat_id):
    file_path = os.path.join(CHAT_DIRECTORY, f"{chat_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)