import requests

url = r"http://127.0.0.1:8000/"
endpoint = "rategame/"

user = {"id": 1234, "name": "user1"}
user_prefs = {"user_id": 1234, "platform_id" : [6, 508], "online" : [True, False], "offline" : [False, True]}
user_ratings = {"user_id" : 1234, "game_id" : 126459, "rating" : 85}

data = requests.post(url + endpoint, json = user_ratings)

print(data.json())

