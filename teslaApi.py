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
def apiAccess(endpoint, d={}):
	# Check that tesla_config.json exists
	if not Path(tesla_config_file).is_file():
		print("Missing {}!".format(tesla_config_file))
		return 1

	# Print which endpoint we're trying to access
	print("apiAccess({0})".format(endpoint))

	if endpoint not in api:
		print("Unknown API endpoint: {}!".format(endpoint))
		return 1

	# Generate headers
	auth_payload = json.load(open(tesla_config_file))
	auth_req = requests.post(AUTH_URL, data=auth_payload)
	auth_resp = json.loads(auth_req.text)
	headers = {"Authorization": "Bearer {}".format(auth_resp['access_token'])}

	# Get Vehicle ID
	vehID_req = requests.get(BASE_API_URL, headers=headers)
	vehID_resp = json.loads(vehID_req.text)
	vehID = vehID_resp['response'][0]['id_s']

	# Wake up the car
	for i in range(1,4):
		wake_req = requests.post(BASE_API_URL + vehID + CMD_WAKEUP, headers=headers)

		if wake_req.status_code == 200:
			break
		elif wake_req.status_code == 408:
			print("Wake timeout {}/3".format(i))
			time.sleep(5*i)
		else:
			print("HTTP {} error".format(wake_req.status_code))
			return 1

	# Make Tesla API Access
	for i in range(1,6):
		# Repeat request in case of timesouts
		if api[endpoint][0] == "GET":
			r = requests.get(BASE_API_URL + vehID + api[endpoint][1], headers=headers)
		elif api[endpoint][0] == "POST":
			r = requests.post(BASE_API_URL + vehID + api[endpoint][1], headers=headers, data=d)

		# Break if good response or error, continue to loop if timeout
		if r.status_code == 200:
			return 0
		elif r.status_code == 408:
			# Car probably asleep
			print("Timeout {}/5".format(i))
			time.sleep(5*i)
			continue
		else:
			# Any other reason this doesn't work
			print("HTTP {0} error: {1}".format(r.status_code, url))
			return 1
	print("Unable to connect to Tesla!")
	return 1
