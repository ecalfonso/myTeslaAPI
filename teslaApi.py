import json
import requests
import time

from pathlib import Path

# Define Tesla config file
tesla_config_file = 'tesla_config.json'

#
# Tesla API Definitions
# From: https://timdorr.docs.apiary.io/#reference
#
AUTH_URL = 		"https://owner-api.teslamotors.com/oauth/token/"
BASE_API_URL =		"https://owner-api.teslamotors.com/api/1/vehicles/"

DATA = 			"/data"

STATE_MOBILE_ACCESS =	"/mobile_enabled"
STATE_CHARGE_STATE =	"/data_request/charge_state"
STATE_CLIMATE_SETTING =	"/data_request/climate_state"
STATE_DRIVING_AND_POS = "/data_request/drive_state"
STATE_GUI_SETTINGS =	"/data_request/gui_settings"
STATE_VEHICLE_STATE =	"/data_request/vehicle_state"

CMD_WAKEUP = 		"/wake_up"
CMD_SET_VALET_MODE =	"/command/set_valet_mode"
CMD_RESET_VALET_PIN =	"/command/reset_valet_pin"
CMD_OPEN_CHARGE_PORT =	"/command/charge_port_door_open"
CMD_SET_STANDARD_CHARGE_LIMIT = "/command/charge_standard"
CMD_SET_MAX_CHARGE_LIMIT = "/command/charge_max_range"
CMD_SET_CUSTOM_CHARGE_LIMIT = "/command/set_charge_limit?percent="
CMD_CHARGE_START =	"/command/charge_start"
CMD_CHARGE_STOP =	"/command/charge_stop"
CMD_FLASH_LIGHTS =	"/command/flash_lights"
CMD_HONK_HORN =		"/command/honk_horn"
CMD_UNLOCK_DOOR =	"/command/door_unlock"
CMD_LOCK_DOOR =		"/command/door_lock"
CMD_SET_TEMP =		"/command/set_temps?driver_temp=driver_temp&passenger_temp=passenger_temp"
CMD_START_HVAC =	"/command/auto_conditioning_start"
CMD_STOP_HVAC =		"/command/auto_conditioning_stop"
CMD_REMOTE_START =	"/command/remote_start_drive?password="

api = {
"data": 		["GET", DATA],
"start_hvac":		["POST", CMD_START_HVAC],
"stop_hvac":		["POST", CMD_STOP_HVAC]
}

#
# Define Functions
#
def buildNotification(endpoint, data):
	cur_temp_in_c = data['climate_state']['inside_temp']
	trg_temp_in_c = data['climate_state']['driver_temp_setting']
	cur_temp = round((cur_temp_in_c*(9/5))+32)
	trg_temp = round((trg_temp_in_c*(9/5))+32)

	if endpoint == "start_hvac":
		if cur_temp < trg_temp:
			return "Heating car from {0}F to {1}F".format(cur_temp, trg_temp)
		else:
			return "Cooling car from {0}F to {1}F".format(cur_temp, trg_temp)
	elif endpoint == "stop_hvac":
		return "HVAC Stopped at {0}F".format(cur_temp)
			

def apiAccess(endpoint, d={}):
	# Check that tesla_config.json exists
	if not Path(tesla_config_file).is_file():
		print("Missing {}!".format(tesla_config_file))
		return "TeslaAPI Failure", "Server missing config file"

	# Print which endpoint we're trying to access
	print("apiAccess({0})".format(endpoint))
	if endpoint not in api:
		print("Unknown API endpoint: {}!".format(endpoint))
		return "TeslaApi Failure!", "Invalid API endpoint {}".format(endpoint)

	# Generate headers
	auth_payload = json.load(open(tesla_config_file))
	auth_req = requests.post(AUTH_URL, data=auth_payload)
	if auth_req.status_code == 200:
		auth_resp = json.loads(auth_req.text)
		headers = {"Authorization": "Bearer {}".format(auth_resp['access_token'])}
	else:
		return "TeslaApi Failure!", "Unable to get Authorization access_token"

	# Get Vehicle ID
	vehID_req = requests.get(BASE_API_URL, headers=headers)
	if vehID_req.status_code == 200:
		vehID_resp = json.loads(vehID_req.text)
		vehID = vehID_resp['response'][0]['id_s']
	else:
		return "TeslaApi Failure!", "Unable to get Vehicle ID"

	# Get Vehicle Data
	for i in range(1,6):
		data_req = requests.get(BASE_API_URL + vehID + DATA, headers=headers)

		if data_req.status_code == 200:
			data = json.loads(data_req.text)['response']
			break
		elif data_req.status_code == 408:
			print("Data timeout {}/5".format(i))
			time.sleep(5*i)
		else:
			print("HTTP {} error".format(data_req.status_code))
			return "TeslaApi Failure!", "Unable to get car Data! HTTP {}".format(wake_req.status_code)

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

	# Make Tesla API Access
	for i in range(1,6):
		# Repeat request in case of timesouts
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
	print("Unable to connect to Tesla!")
	return "TeslaApi Failure!", "Car timed out!"
