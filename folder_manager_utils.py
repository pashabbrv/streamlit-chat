import json

def load_folders():
    try:
        with open('folders.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['folders']
    except FileNotFoundError:
        return []

def save_folders(folders):
    with open('folders.json', 'w', encoding='utf-8') as f:
        json.dump({"folders": folders}, f, ensure_ascii=False, indent=4)

def add_folder(folders, folder_name):
    if folder_name and folder_name not in [folder['folder_name'] for folder in folders]:
        new_folder = {
            "folder_name": folder_name,
            "chats": []
        }
        folders.append(new_folder)
        save_folders(folders)
        return True
    return False

def remove_folder(folders, folder_name):
    for folder in folders:
        if folder['folder_name'] == folder_name:
            folders.remove(folder)
            save_folders(folders)
            return True
    return False

def add_chat_to_folder(folders, folder_name, chat_name):
    for folder in folders:
        if folder['folder_name'] == folder_name:
            folder['chats'].append({"chat_name": chat_name})
            save_folders(folders)
            return True
    return False

def remove_chat_from_folder(folders, folder_name, chat_name):
    for folder in folders:
        if folder['folder_name'] == folder_name:
            folder['chats'] = [chat for chat in folder['chats'] if chat['chat_name'] != chat_name]
            save_folders(folders)
            return True
    return False
