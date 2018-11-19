import json
import math
import requests
import time

from pathlib import Path

# Define Tesla config file
tesla_config_file = "tesla_config.json"
tesla_token_file =  "tesla_token.json"

#
# Tesla API Definitions
# From: https://timdorr.docs.apiary.io/#reference
#
AUTH_URL =      "https://owner-api.teslamotors.com/oauth/token/"
BASE_API_URL =  "https://owner-api.teslamotors.com/api/1/vehicles/"

DATA =                  "/data"

STATE_MOBILE_ACCESS =	"/mobile_enabled"
STATE_CHARGE_STATE =	"/data_request/charge_state"
STATE_CLIMATE_SETTING =	"/data_request/climate_state"
STATE_DRIVING_AND_POS = "/data_request/drive_state"
STATE_GUI_SETTINGS =	"/data_request/gui_settings"
STATE_VEHICLE_STATE =	"/data_request/vehicle_state"

CMD_WAKEUP =            "/wake_up"
CMD_SET_VALET_MODE =	"/command/set_valet_mode"
CMD_RESET_VALET_PIN =	"/command/reset_valet_pin"
CMD_CLOSE_CHARGE_PORT =	"/command/charge_port_door_close"
CMD_OPEN_CHARGE_PORT =	"/command/charge_port_door_open"
CMD_SET_STANDARD_CHARGE_LIMIT = "/command/charge_standard"
CMD_SET_MAX_CHARGE_LIMIT = "/command/charge_max_range"
CMD_SET_CUSTOM_CHARGE_LIMIT = "/command/set_charge_limit?percent="
CMD_CHARGE_START =	    "/command/charge_start"
CMD_CHARGE_STOP =	    "/command/charge_stop"
CMD_FLASH_LIGHTS =	    "/command/flash_lights"
CMD_HONK_HORN =		    "/command/honk_horn"
CMD_UNLOCK_DOOR =	    "/command/door_unlock"
CMD_LOCK_DOOR =		    "/command/door_lock"
CMD_SET_TEMP =		    "/command/set_temps?driver_temp=driver_temp&passenger_temp=passenger_temp"
CMD_START_HVAC =    	"/command/auto_conditioning_start"
CMD_STOP_HVAC =		    "/command/auto_conditioning_stop"
CMD_REMOTE_START =	    "/command/remote_start_drive?password="

api = {
    "data": 		    ["GET", DATA],
    "close_charge_port": ["POST", CMD_CLOSE_CHARGE_PORT],
    "open_charge_port": ["POST", CMD_OPEN_CHARGE_PORT],
    "start_hvac":	    ["POST", CMD_START_HVAC],
    "stop_hvac":	    ["POST", CMD_STOP_HVAC]
}

#
# Define Functions
#
def buildNotification(endpoint, data):
    # Print raw data
    print(data)

    # Climate data
    cur_temp_in_c = data['climate_state']['inside_temp']
    out_temp_in_c = data['climate_state']['outside_temp']
    trg_temp_in_c = data['climate_state']['driver_temp_setting']
    cur_temp = round((cur_temp_in_c*(9/5))+32)
    out_temp = round((out_temp_in_c*(9/5))+32)
    trg_temp = round((trg_temp_in_c*(9/5))+32)

    # Charge Port
    charge_port_door_open = data['charge_state']['charge_port_door_open']
    charge_port_latch = data['charge_state']['charge_port_latch']

    # Charge State
    battery_level = data['charge_state']['battery_level']
    battery_range = round(data['charge_state']['battery_range'])
    charge_limit_soc = data['charge_state']['charge_limit_soc']
    charge_miles_added_rated  = data['charge_state']['charge_miles_added_rated']
    # Charging, Complete (Plugged but not charging), Disconnected, Stopped (Check scheduled_charging_pending)
    charging_state  = data['charge_state']['charging_state']
    scheduled_charging_pending = data['charge_state']['scheduled_charging_pending']
    scheduled_charging_start_time = data['charge_state']['scheduled_charging_start_time']
    time_to_full_charge_in_dec = data['charge_state']['time_to_full_charge'] # 60 * X = minutes

    # Vehicle State
    locked =  data['vehicle_state']['locked']
    door_status = data['vehicle_state']['df'] | data['vehicle_state']['pf'] |\
                  data['vehicle_state']['dr'] | data['vehicle_state']['pr'] |\
                  data['vehicle_state']['ft'] | data['vehicle_state']['rt']
    vehicle_name = data['vehicle_state']['vehicle_name']

    # Build first line with data relevant to endpoint
    msg = ""
    if endpoint == "close_charge_port":
        msg += "Charge Port Closed\n"
    elif endpoint == "open_charge_port":
        msg += "Charge Port Open and Unlocked\n"
    elif endpoint == "start_hvac":
        if cur_temp < trg_temp:
            msg += "Heating {0} from {1}F to {2}F\nOutside Temp: {3}F\n".format(
                        vehicle_name,cur_temp, trg_temp, out_temp)
        else:
            msg += "Cooling {0} from {1}F to {2}F\nOutside Temp: {3}F\n".format(
                        vehicle_name, cur_temp, trg_temp, out_temp)
    elif endpoint == "stop_hvac":
        msg += "{0} HVAC Stopped at {1}F\nOutside Temp: {2}F\n".format(vehicle_name, cur_temp, out_temp)

    # Alert if Car is Unlocked
    if locked != True:
        msg+= "{0} is Unlocked!\n".format(vehicle_name)

    # Alert if Doors/Trunks are open
    if (door_status & 0x1):
        msg += "Driver Front Door open!\n"
    if (door_status & 0x2):
        msg += "Passenger Front Door open!\n"
    if (door_status & 0x4):
        msg += "Driver Rear Door open!\n"
    if (door_status & 0x8):
        msg += "Passenger Rear Door open!\n"
    if (door_status & 0x10):
        msg += "Front Trunk open!\n"
    if (door_status & 0x20):
        msg += "Rear Trunk open!\n"

    # Append Charge data
    msg += "Current Range: {0} miles ({1}%)\n".format(battery_range, battery_level)
    if charging_state == "Charging":
        msg += "{} miles ({}%) added this session.\n".format(charge_miles_added_rated,
        round((charge_miles_added_rated/310)*100))
        hours = math.floor(time_to_full_charge_in_dec)
        mins = round(60 * (time_to_full_charge_in_dec - hours))
        msg += "Time til full charge ({0}%):".format(charge_limit_soc)
        if hours > 0:
            msg += " {}hr".format(hours)
        msg += " {}min\n".format(mins)
    elif charging_state == "Stopped":
        if scheduled_charging_pending == True:
            msg += "Charging will begin {}".format(
                time.strftime("%A at %I:%M %p", time.localtime(scheduled_charging_start_time)))
        else:
            msg += "Charging is Stopped\n"

    return msg

def apiAccess(endpoint, d={}):
    # Print which endpoint we're trying to access
    print("apiAccess({0})".format(endpoint))
    if endpoint not in api:
        print("Unknown API endpoint: {}!".format(endpoint))
        return "TeslaApi Failure!", "Invalid API endpoint {}".format(endpoint)

    # Check that tesla_config.json exists
    if not Path(tesla_config_file).is_file():
        print("Missing {}!".format(tesla_config_file))
        return "TeslaAPI Failure", "Server missing config file"

    # Access token logic
    if Path(tesla_token_file).is_file():
        current_token = json.load(open(tesla_token_file))
        if round(time.time()) < current_token["created_at"] + current_token["expires_in"]:
            # Access token should be valid
            print("Using known access_token")
            headers = {"Authorization": "Bearer {}".format(current_token["access_token"])}
        else:
            # Use Refresh token to get Access Token
            print("Using refresh_token")
            auth_payload = \
            {
            "client_id":"81527cff06843c8634fdc09e8ac0abefb46ac849f38fe1e431c2ef2106796384",
            "client_secret":"c7257eb71a564034f9419ee651c7d0e5f7aa6bfbd18bafb5c5c033b093bb2fa3",
            "grant_type":"refresh_token",
            "refresh_token":current_token["refresh_token"]
            }
            auth_req = requests.post(AUTH_URL, data=auth_payload)
            if auth_req.status_code == 200:
                auth_resp = json.loads(auth_req.text)
                headers = {"Authorization": "Bearer {}".format(auth_resp['access_token'])}
                # Dump token into tesla_token.json file
                with open(tesla_token_file, 'w') as outfile:
                    json.dump(auth_resp, outfile)
                    outfile.close()
            else:
                return "TeslaApi Failure!", "Unable to get Authorization access_token"
    else:
        # Use Tesla credentials to get Access Token
        print("Using Tesla credentials")
        auth_payload = json.load(open(tesla_config_file))
        auth_req = requests.post(AUTH_URL, data=auth_payload)
        if auth_req.status_code == 200:
            auth_resp = json.loads(auth_req.text)
            headers = {"Authorization": "Bearer {}".format(auth_resp['access_token'])}
            # Dump token into tesla_token.json file
            with open(tesla_token_file, 'w') as outfile:
                    json.dump(auth_resp, outfile)
                    outfile.close()
        else:
            return "TeslaApi Failure!", "Unable to get Authorization access_token"

    # Get Vehicle ID
    vehID_req = requests.get(BASE_API_URL, headers=headers)
    if vehID_req.status_code == 200:
        vehID_resp = json.loads(vehID_req.text)
        vehID = vehID_resp['response'][0]['id_s']
    else:
        return "TeslaApi Failure!", "Unable to get Vehicle ID"

    # Wake up the car
    for i in range(1,6):
        wake_req = requests.post(BASE_API_URL + vehID + CMD_WAKEUP, headers=headers)

        if wake_req.status_code == 200:
            break
        elif wake_req.status_code == 408:
            print("Wake timeout {}/5".format(i))
            time.sleep(5*i)
        else:
            print("HTTP {} error".format(wake_req.status_code))
            return "TeslaApi Failure!", "Unable to wakeup car! HTTP {}".format(wake_req.status_code)

    # Get Vehicle Data
    data_flag = 0
    for i in range(1,6):
        data_req = requests.get(BASE_API_URL + vehID + DATA, headers=headers)

        if data_req.status_code == 200:
            data = json.loads(data_req.text)['response']
            data_flag = 1
            break
        elif data_req.status_code == 408:
            print("Data timeout {}/5".format(i))
            time.sleep(5*i)
        else:
            print("HTTP {} error".format(data_req.status_code))
            return "TeslaApi Failure!", "Unable to get car Data! HTTP {}".format(wake_req.status_code)

    if data_flag == 0:
        return "TeslaApi Failure!", "Unable to get car Data! Timeout limit reached!"

    # Make Tesla API Access
    for i in range(1,6):
        if api[endpoint][0] == "GET":
            api_req = requests.get(BASE_API_URL + vehID + api[endpoint][1], headers=headers)
        elif api[endpoint][0] == "POST":
            api_req = requests.post(BASE_API_URL + vehID + api[endpoint][1], headers=headers, data=d)

        if api_req.status_code == 200:
            return "TeslaAPI Success", buildNotification(endpoint, data)
        elif api_req.status_code == 408:
            print("Timeout {}/5".format(i))
            time.sleep(5*i)
            continue
        else:
            print("HTTP {0} error: {1}".format(api_req.status_code, url))
            return "TeslaApi Failure!", "Unable to wakeup car! HTTP {}".format(api_req.status_code)

    # If we reach here, API access failed
    print("Unable to connect to Tesla!")
    return "TeslaApi Failure!", "Car timed out during API access!"
