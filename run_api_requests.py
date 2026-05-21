import requests

url = r"http://127.0.0.1:8000/"

user = {"name": "user1"}
user_prefs = {"platform_id": [6, 508], "online": [True, False], "offline": [False, True]}
user_ratings = {"game_id": 126459, "rating": 95}

user_response = requests.post(url + "create_user/", json=user)
print("user response:", user_response.json())
creator_id = user_response.json().get("id")

if creator_id is None:
    raise RuntimeError("Failed to create user; cannot continue group creation")

group = {"name": "di teamma", "user_id": creator_id}
endpoint = "create_group/"
data = requests.post(url + endpoint, json=group)
print("group response:", data.json())

