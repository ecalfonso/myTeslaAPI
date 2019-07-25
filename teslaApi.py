import json
import math
import requests
import time

from pathlib import Path

# Define Tesla config file
tesla_config_file   = "tesla_default_auth_body.json"
tesla_endpoint_file = "ownerapi_endpoints.json"
tesla_env_file      = "env.json"
tesla_token_file    = "tesla_current_token.json"

#
# Define Functions
#
def loadApi():
    if not Path(tesla_endpoint_file).is_file():
        print("Tesla API endpoint file missing: {}!".format(tesla_ownerapi_file))
        return -1

    return json.load(open(tesla_endpoint_file))

def loadEnv():
    if not Path(tesla_env_file).is_file():
        print("Tesla Env file missing: {}".format(tesla_env_file))
        return -1
    return json.load(open(tesla_env_file))

def getHeaders(api, env):
    if not Path(tesla_config_file).is_file():
        print("Tesla config file missing: {}!".format(tesla_config_file))
        return -1

    JSON_HEADERS = {"Content-type":"application/json"}

    if Path(tesla_token_file).is_file():
        current_token = json.load(open(tesla_token_file))
        if round(time.time()) < current_token["created_at"] + current_token["expires_in"]:
            JSON_HEADERS["Authorization"] = "Bearer {}".format(current_token["access_token"])
            return JSON_HEADERS
        else:
            REFRESH_PAYLOAD = {"grant_type":"refresh_token"}
            REFRESH_PAYLOAD["client_id"] = env["OWNERAPI_CLIENT_ID"]
            REFRESH_PAYLOAD["client_secret"] = env["OWNERAPI_CLIENT_SECRET"]
            REFRESH_PAYLOAD["refresh_token"] = current_token["refresh_token"]
            auth_req = requests.post(env["OWNERAPI_BASE_URL"] + \
                    api["AUTHENTICATE"]["URI"], data=REFRESH_PAYLOAD)
            if auth_req.status_code == 200:
                auth_resp = json.loads(auth_req.text)
                JSON_HEADERS["Authorization"] = "Bearer {}".format(auth_resp['access_token'])
                # Dump token into tesla_token.json file
                with open(tesla_token_file, 'w') as outfile:
                    json.dump(auth_resp, outfile)
                    outfile.close()
                    return JSON_HEADERS
            else:
                print("Unable to get access_token from refresh_token")
                return -1
    else:
        auth_payload = json.load(open(tesla_config_file))
        auth_req = requests.post(env["OWNERAPI_BASE_URL"] + \
                api["AUTHENTICATE"]["URI"], data=auth_payload)
        if auth_req.status_code == 200:
            auth_resp = json.loads(auth_req.text)
            JSON_HEADERS["Authorization"] = "Bearer {}".format(auth_resp["access_token"])
            # Dump token into tesla_token.json file
            with open(tesla_token_file, 'w') as outfile:
                json.dump(auth_resp, outfile)
                outfile.close()

            return JSON_HEADERS
        else:
            print("Unable to get access_token from Tesla credentials!")
            return -1

def getVehicleID(api, env, headers):
    vehID_req = requests.get(env["OWNERAPI_BASE_URL"] + \
            api["VEHICLE_LIST"]["URI"], headers=headers)
    if vehID_req.status_code == 200:
        return json.loads(vehID_req.text)['response'][0]['id_s']
    else:
        if wake_req.status_code:
            print("Unable to get Vehicle ID! Http error {}".format(wake_req.status_code))
        else:
            print("Unable to get Vehicle ID!")
        return -1

def access(endpoint, data={}):
    # Check/Load Tesla API Endpoints
    api = loadApi()
    if api == -1:
        print("Unable to load Tesla API!")
        return -1
    env = loadEnv()
    if env == -1:
        print("Unable to load Tesla Env!")
        return -1

    # Check if endpoint exists
    if endpoint not in api:
        print("{} does not exist in the Tesla API!".format(endpoint))
        return -1

    # Tesla API Auth Logic
    headers = getHeaders(api, env)
    if headers == -1:
        print("Unable to generate HTTP headers!")
        return -1

    # Get Vehicle ID
    vehID = getVehicleID(api, env, headers)
    if vehID == -1:
        print("Unable to get Vehicle ID!")
        return -1

    # Make API Access
    if api[endpoint]["TYPE"] == "GET":
        api_req = requests.get(env["OWNERAPI_BASE_URL"] + \
                api[endpoint]["URI"].format(vehicle_id=vehID), headers=headers)
    elif api[endpoint]["TYPE"] == "POST":
        api_req = requests.post(env["OWNERAPI_BASE_URL"] + \
                api[endpoint]["URI"].format(vehicle_id=vehID), headers=headers, data=data)

    # check response
    if api_req.status_code == 200:
        return json.loads(api_req.text)["response"]
    else:
        if api_req.status_code:
            print("Tesla API Access failed! Http error {}\n{}\n".format(
                api_req.status_code, api_req.text))
        else:
            print("Tesla API Access failed!")
        return -1

def carWakeUp():
    # Check/Load Tesla API Endpoints
    api = loadApi()
    if api == -1:
        print("Unable to load Tesla API!")
        return -1
    env = loadEnv()
    if env == -1:
        print("Unable to load Tesla Env!")
        return -1

    # Tesla API Auth Logic
    headers = getHeaders(api, env)
    if headers == -1:
        print("Unable to generate HTTP headers!")
        return -1

    # Get Vehicle ID
    vehID = getVehicleID(api, env, headers)
    if vehID == -1:
        print("Unable to get Vehicle ID!")
        return -1

    # Loop polling sleep status and send wake_up while asleep/offline
    for i in range (1,46):
        sleepStatus_req = requests.get(env["OWNERAPI_BASE_URL"] + \
                api["VEHICLE_LIST"]["URI"], headers=headers)

        if sleepStatus_req.status_code == 200:
            sleepStatus_resp = json.loads(sleepStatus_req.text)
            if sleepStatus_resp["response"][0]["state"] in ["asleep", "offline"]:
                print("Wakeup request {}/45 - Sleep Status: {}".format(
                    i, sleepStatus_resp["response"][0]["state"]))
                requests.post(env["OWNERAPI_BASE_URL"] + \
                        api["WAKE_UP"]["URI"].format(vehicle_id=vehID), headers=headers)
                time.sleep(1)
            elif sleepStatus_resp["response"][0]["state"] == "online":
                return 0
        else:
            if sleepStatus_req.status_code:
                print("Unable to get Vehicle Sleep Status! Http error {}".format(sleepStatus_req.status_code))
            else:
                print("Unable to get Vehicle Sleep Status!")
            return -1

def testLogin():
    # Check/Load Tesla API Endpoints
    api = loadApi()
    if api == -1:
        print("Unable to load Tesla API!")
        return -1
    env = loadEnv()
    if env == -1:
        print("Unable to load Tesla Env!")
        return -1

    # Tesla API Auth Logic
    headers = getHeaders(api, env)
    if headers == -1:
        print("Unable to generate HTTP headers!")
        return -1

    return 0
