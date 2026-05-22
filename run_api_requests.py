import requests

url = r"http://127.0.0.1:8000/"

#Create the first user
user1 = {"name": "user1"}
user1_prefs = {"platform_id": [6, 508], "online": [True, False], "offline": [False, True]}
user1_ratings = {"game_id": 126459, "rating": 95}

#Make the call to add them to the database
endpoint = "create_user/"
user1_response = requests.post(url + endpoint, json=user1)
print("user1 response:", user1_response.json())
user1_id = user1_response.json().get("id")

if user1_id is None:
    raise RuntimeError("Failed to create user; cannot continue group creation")



#Create the group and make the call to add it to the database
group = {"name": "di teamma", "user_id": user1_id}
endpoint = "create_group/"
group_response = requests.post(url + endpoint, json=group)
print("group response:", group_response.json())
group_id = group_response.json().get("id")




#Create the second user
user2 = {"name": "user2"}
user2_prefs = {"platform_id": [6, 167], "online": [True, True], "offline": [False, True]}
user2_ratings = {"game_id": 126459, "rating": 70}


#Add the second user to the database
endpoint = "create_user/"
user2_response = requests.post(url + endpoint, json=user2)
print("user2 response:", user2_response.json())
joiner_id = user2_response.json().get("id")




#Add user2 to user1's group
join_data = {"user_id" : joiner_id, "group_id": group_id}
endpoint = "join_group/"
data = requests.post(url + endpoint, json = join_data)
print("Joining")
print(data.json())




#Remove user2 from user1's group
endpoint = "leave_group/"
data = requests.delete(url + endpoint, json = join_data)
print("Leaving")
print(data.json())
