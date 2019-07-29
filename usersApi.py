import json

users_file = "users_config.json"

def access_grant(username):
    users = json.load(open(users_file))
    for i in range(0, len(users) - 1):
        if users[i]["user"] == username:
            if users[i]["type"] == "owner":
                return -1
            users[i]["access"] = True
            with open(users_file, "w") as outfile:
                json.dump(users, outfile)
                outfile.close()
            return 0
    return -1

def access_deny(username):
    users = json.load(open(users_file))
    for i in range(0, len(users) - 1):
        if users[i]["user"] == username:
            if users[i]["type"] == "owner":
                return -1
            users[i]["access"] = False
            with open(users_file, "w") as outfile:
                json.dump(users, outfile)
                outfile.close()
            return 0
    return -1

def get_user(user, secret):
    users = json.load(open(users_file))
    for u in users:
        if u["user"] == user and u["pw"] == secret:
            return u
    return -1

def is_user(username):
    users = json.load(open(users_file))
    for u in users:
        if u["user"] == username:
            return 0
    return -1
