import json
import os
import time

USERS_FILE = "users.json"
FORUM_FILE = "forum.json"

def _load(f):
    if not os.path.exists(f):
        return {}
    with open(f, "r", encoding="utf-8") as file:
        return json.load(file)

def _save(f, data):
    with open(f, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

def add_user(user_id, username):
    users = _load(USERS_FILE)
    if str(user_id) not in users:
        users[str(user_id)] = {"username": username}
        _save(USERS_FILE, users)

def get_all_users():
    return list(_load(USERS_FILE).keys())

def get_forum():
    return _load(FORUM_FILE)

def create_topic(user_id, username, title, first_post_text):
    forum = get_forum()
    tid = str(int(time.time()))
    forum[tid] = {
        "title": title,
        "author_id": user_id,
        "author_name": username,
        "created": time.time(),
        "posts": [
            {
                "user_id": user_id,
                "username": username,
                "text": first_post_text,
                "time": time.time()
            }
        ]
    }
    _save(FORUM_FILE, forum)
    return tid

def add_post(topic_id, user_id, username, text):
    forum = get_forum()
    if topic_id in forum:
        forum[topic_id]["posts"].append({
            "user_id": user_id,
            "username": username,
            "text": text,
            "time": time.time()
        })
        _save(FORUM_FILE, forum)
        return True
    return False