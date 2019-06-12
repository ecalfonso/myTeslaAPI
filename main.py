import joinApi
import json
import math
import teslaApi
import time
import sys

from enum import Enum
########################################
#
# Define Global Vars
#
########################################
ERR_MSG = "TeslaAPI Failure!"
SUC_MSG = "TeslaAPI"

CMD_LIST = "DATA \
        DUMP \
        LOCK \
        AC_ON \
        AC_OFF \
        CHARGE_PORT_OPEN \
        CHARGE_PORT_CLOSE \
        CHARGE_START \
        CHARGE_STOP \
        HONK_HORN \
        FLASH_LIGHTS \
        SENTRY_MODE_ON \
        SENTRY_MODE_OFF \
        SET_CHARGE_LIMIT \
        SEAT_HEATER_ON \
        SEAT_HEATER_OFF"

CMD = Enum("CMD", CMD_LIST)

########################################
#
# Parse incoming command
#
########################################
user_cmd = sys.argv[1].lower()

if user_cmd in [
        "data",
        "status"
        ]:
    cmd = CMD.DATA
elif user_cmd in [
        "dump"
        ]:
    cmd = CMD.DUMP
elif user_cmd in [
        "turn on the ac",
        "turn on the air conditioner",
        "turn on the fans",
        "warm up"
        ]:
    cmd = CMD.AC_ON
elif user_cmd in [
        "turn off the ac",
        "turn off the air conditioner",
        "turn off the fans",
        "stop warming up"
        ]:
    cmd = CMD.AC_OFF
elif user_cmd in [
        "open the charge port",
        "unlock the charge port",
        "open the charger port",
        "unlock the charger port"
        ]:
    cmd = CMD.CHARGE_PORT_OPEN
elif user_cmd in [
        "close the charge port",
        "lock the charge port",
        "close the charger port",
        "lock the charger port"
        ]:
    cmd = CMD.CHARGE_PORT_CLOSE
elif user_cmd in [
        "lock the car",
        "lock the doors"
        ]:
    cmd = CMD.LOCK
elif user_cmd in [
        "start charging",
        "begin charging",
        "charge now"
        ]:
    cmd = CMD.CHARGE_START
elif user_cmd in [
        "stop charging",
        "end charging"
        ]:
    cmd = CMD.CHARGE_STOP
elif user_cmd in [
        "honk the horn"
        ]:
    cmd = CMD.HONK_HORN
elif user_cmd in [
        "flash the lights"
        ]:
    cmd = CMD.FLASH_LIGHTS
elif user_cmd in [
        "turn on sentry mode",
        "turn on security",
        "watch yourself"
        ]:
    cmd = CMD.SENTRY_MODE_ON
elif user_cmd in [
        "turn off sentry mode",
        "turn off security",
        "stop watching youself"
        ]:
    cmd = CMD.SENTRY_MODE_OFF
elif "set the charge limit to" in user_cmd \
        or "set charge limit to" in user_cmd:
    cmd = CMD.SET_CHARGE_LIMIT

    percent = user_cmd.split(' ')[-1]
    if percent in [
            'percent',
            '%']:
        percent = user_cmd.split(' ')[-2]

    if percent == 'max':
        percent = 100
    elif percent == 'normal':
        percent = 90
    else:
        if percent[-1] == '%':
            percent = percent[:-1]
        if percent.isdigit():
            percent = int(percent)
            percent = min(percent, 100)
            percent = max(percent, 50)
        else:
            joinApi.push(ERR_MSG, "Invalid Charge Limit: {}".format(percent))
            exit()
elif "seat heater" in user_cmd:
    if "set" in user_cmd:
        cmd = CMD.SEAT_HEATER_ON
        try:
            seat_heater_level = user_cmd.split(' ')[-1]
            if int(seat_heater_level) < 1 or 3 < int(seat_heater_level):
                joinApi.push(ERR_MSG, "Invalid Seat Heater Level: {}".format(user_cmd.split(' ')[-1]))
                exit()
        except:
            joinApi.push(ERR_MSG, "Invalid Seat Heater input: {}".format(user_cmd))
            exit()

    else:
        cmd = CMD.SEAT_HEATER_OFF

    if "driver" in user_cmd:
        seat_heater_id = 0
        seat_heater_str = "Driver's seat"
    elif "passenger" in user_cmd:
        seat_heater_id = 1
        seat_heater_str = "Passenger's seat"
    elif "back left" in user_cmd:
        seat_heater_id = 2
        seat_heater_str = "Rear Driver's seat"
    elif "back middle" in user_cmd:
        seat_heater_id = 4
        seat_heater_str = "Rear Middle seat"
    elif "back right" in user_cmd:
        seat_heater_id = 5
        seat_heater_str = "Rear Passenger's seat"

else:
    print("Unable to process input string: {}".format(user_cmd))
    joinApi.push(ERR_MSG, "Unable to process input string: {}".format(user_cmd))
    exit()

########################################
#
# Wake up car
#
########################################
if teslaApi.carWakeUp() == -1:
    print("Unable to wakeup Tesla!")
    joinApi.push(ERR_MSG, "Unable to wakeup Tesla!")
    exit()

########################################
#
# Get initial car data and extract data
#
########################################
data = teslaApi.access("VEHICLE_DATA")
if data == -1:
    print("Unable to get Vehicle data!")
    joinApi.push(ERR_MSG, "Unable to get Vehicle data!")
    exit()

# Extract climate data
inner_temp = round(((data['climate_state']['inside_temp'])*(9/5)) + 32)
outer_temp = round(((data['climate_state']['outside_temp'])*(9/5)) + 32)
target_temp = round(((data['climate_state']['driver_temp_setting'])*(9/5)) + 32)

# Extract Charge Port data
charge_port_door_open = data['charge_state']['charge_port_door_open']
charge_port_latch = data['charge_state']['charge_port_latch']

# Charge State
battery_level = data['charge_state']['battery_level']
battery_range = round(data['charge_state']['battery_range'])
charge_limit_soc = data['charge_state']['charge_limit_soc']
charge_miles_added_rated  = data['charge_state']['charge_miles_added_rated']
charge_rate = data['charge_state']['charge_rate']
charge_rate_units = data['gui_settings']['gui_charge_rate_units']
charging_state  = data['charge_state']['charging_state']
scheduled_charging_pending = data['charge_state']['scheduled_charging_pending']
scheduled_charging_start_time = data['charge_state']['scheduled_charging_start_time']
time_to_full_charge_in_dec = data['charge_state']['time_to_full_charge']

# Vehicle State
locked =  data['vehicle_state']['locked']
door_status = \
        data['vehicle_state']['df'] | data['vehicle_state']['pf'] |\
        data['vehicle_state']['dr'] | data['vehicle_state']['pr'] |\
        data['vehicle_state']['ft'] | data['vehicle_state']['rt']
vehicle_name = data['vehicle_state']['vehicle_name']
sentry_mode = data['vehicle_state']['sentry_mode']
sw_update_status = data['vehicle_state']['software_update']['status']

########################################
#
# Process initial data before executing User command
#
########################################
msg = ""
if cmd == CMD.DATA:
    if sw_update_status != "":
        msg += "Software Update Status: {}\n".format(sw_update_status)
    if data["climate_state"]["is_preconditioning"] == True:
        msg += "Auto conditioning from {}F to {}F, Outside temp: {}F\n".format(
                inner_temp, target_temp, outer_temp)

elif cmd == CMD.DUMP:
    print(data)
    joinApi.push(SUC_MSG, json.dumps(data))
    exit()

elif cmd == CMD.AC_ON:
    if data["climate_state"]["is_preconditioning"] == False:
        cmd_resp = teslaApi.access("CLIMATE_ON")
        if cmd_resp == -1:
            msg += "Failed to turn AC on for {0}!\n".format(vehicle_name)
        else:
            if inner_temp < target_temp:
                msg += "Heating {0} from {1}F to {2}F\nOutside Temp: {3}F\n".format(
                        vehicle_name, inner_temp, target_temp, outer_temp)
            else:
                msg += "Cooling {0} from {1}F to {2}F\nOutside Temp: {3}F\n".format(
                        vehicle_name, inner_temp, target_temp, outer_temp)
    else:
        msg += "AC is already on for {0}. Inner Temp is {1}F\n".format(vehicle_name, inner_temp)

elif cmd == CMD.AC_OFF:
    if data["climate_state"]["is_preconditioning"] == True:
        cmd_resp = teslaApi.access("CLIMATE_OFF")
        if cmd_resp == -1:
            msg += "Failed to turn AC off for {0}!\n".format(vehicle_name)
        else:
            msg += "{0} HVAC Stopped at {1}F\nOutside Temp: {2}F\n".format(vehicle_name, inner_temp, outer_temp)
    else:
        msg += "AC/Fans are already off for {0}\n".format(vehicle_name)

elif cmd == CMD.CHARGE_PORT_CLOSE:
    if charge_port_door_open == False:
        msg += "Charge Port already closed for {0}\n".format(vehicle_name)
    else:
        if charge_port_latch == "Engaged":
            msg += "Charge Port open and engaged. May be charging! Will not close Charge Port for {0}\n".format(
                    vehicle_name)
        else:
            cmd_resp = teslaApi.access("CHARGE_PORT_DOOR_CLOSE")
            if cmd_resp == -1:
                msg += "Failed to close Charge Port for {0}!\n".format(vehicle_name)
            else:
                msg += "Closing Charge Port for {0}\n".format(vehicle_name)

elif cmd == CMD.CHARGE_PORT_OPEN:
    if charge_port_door_open == True:
        if charge_port_latch == "Engaged":
            cmd_resp = teslaApi.access("CHARGE_PORT_DOOR_OPEN")
            if cmd_resp == -1:
                msg += "Failed to Unlock Charge Port for {0}!\n".format(vehicle_name)
            else:
                msg += "Unlocking Charge Port for {0}\n".format(vehicle_name)
        else:
            msg += "Charge Port already open for {0}\n".format(vehicle_name)
    else:
        cmd_resp = teslaApi.access("CHARGE_PORT_DOOR_OPEN")
        if cmd_resp == -1:
            msg += "Failed to Open Charge Port for {0}!\n".format(vehicle_name)
        else:
            msg += "Opening Charge Port for {0}\n".format(vehicle_name)

elif cmd == CMD.LOCK:
    if locked == True:
        msg += "{0} is already locked!\n".format(vehicle_name)
    else:
        cmd_resp = teslaApi.access("LOCK")
        if cmd_resp == -1:
            msg += "Failed to lock {0}!\n".format(vehicle_name)
        else:
            msg += "Locking {0}\n".format(vehicle_name)

elif cmd == CMD.CHARGE_START:
    if charging_state == "Stopped":
        cmd_resp = teslaApi.access("START_CHARGE")
        if cmd_resp == -1:
            msg += "Unable to start charging for {0}!\n".format(vehicle_name)
        else:
            msg += "Starting charge for {0}\n".format(vehicle_name)
    else:
        msg += "{0} not currently plugged in\n".format(vehicle_name)

elif cmd == CMD.CHARGE_STOP:
    if charging_state == "Charging":
        cmd_resp = teslaApi.access("STOP_CHARGE")
        if cmd_resp == -1:
            msg += "Unable to stop charging for {0}!\n".format(vehicle_name)
        else:
            msg += "Stopping charge for {0}\n".format(vehicle_name)
    else:
        msg += "{0} not currently charging\n".format(vehicle_name)

elif cmd == CMD.HONK_HORN:
    cmd_resp = teslaApi.access("HONK_HORN")
    if cmd_resp == -1:
        msg += "Unable to honk {0}'s horn!\n".format(vehicle_name)
    else:
        msg += "Honked {0}'s horn\n".format(vehicle_name)

elif cmd == CMD.FLASH_LIGHTS:
    cmd_resp = teslaApi.access("FLASH_LIGHTS")
    if cmd_resp == -1:
        msg += "Unable to flash {0}'s lights".format(vehicle_name)
    else:
        msg += "Flashed {0}'s lights \n".format(vehicle_name)

elif cmd == CMD.SENTRY_MODE_ON:
    if sentry_mode == True:
        msg += "Sentry Mode already active for {}\n".format(vehicle_name)
    else:
        in_data = '{"on":"true"}'
        cmd_resp = teslaApi.access("SET_SENTRY_MODE", data=in_data)
        if cmd_resp == -1:
            msg += "Unable to turn on Sentry Mode for {}\n".format(vehicle_name)
        else:
            msg += "Turning on Sentry Mode for {}\n".format(vehicle_name)

elif cmd == CMD.SENTRY_MODE_OFF:
    if sentry_mode != True:
        msg += "Sentry Mode is not active for {}".format(vehicle_name)
    else:
        in_data = '{"on":"false"}'
        cmd_resp = teslaApi.access("SET_SENTRY_MODE", data=in_data)
        if cmd_resp == -1:
            msg += "Unable to turn off Sentry Mode for {}\n".format(vehicle_name)
        else:
            msg += "Turning off Sentry Mode for {}\n".format(vehicle_name)

elif cmd == CMD.SET_CHARGE_LIMIT:
    in_data = '{"percent":"'+str(percent)+'"}'
    cmd_resp = teslaApi.access("CHANGE_CHARGE_LIMIT", data=str(in_data))
    if cmd_resp == -1:
        msg += "Unable to set {}'s charge limit to {}\n".format(vehicle_name, percent)
    else:
        msg += "Setting {}'s charge limit to {}\n".format(vehicle_name, percent)

elif cmd == CMD.SEAT_HEATER_ON:
    # Turn on preconditioning before sending Seat Heat Req
    if data["climate_state"]["is_preconditioning"] == False:
        cmd_resp = teslaApi.access("CLIMATE_ON")
        if cmd_resp == -1:
            msg += "Failed to turn AC on for {}!\n".format(vehicle_name)
    in_data = '{"heater":"'+str(seat_heater_id)+'", "level":"'+str(seat_heater_level)+'"}'
    cmd_resp = teslaApi.access("REMOTE_SEAT_HEATER_REQUEST", data=str(in_data))
    if cmd_resp == -1:
        msg += "Failed to set {} heater to level {} for {}!\n".format(
                seat_heater_str, seat_heater_level, vehicle_name)
    else:
        msg += "Setting {} heater to level {} for {}\n".format(
                seat_heater_str, seat_heater_level, vehicle_name)


elif cmd == CMD.SEAT_HEATER_OFF:
    # If preconditioning is off, heaters can't be on
    if data["climate_state"]["is_preconditioning"] == False:
         msg += "Seat Heaters are not on for {}!\n".format(vehicle_name)
    else:
        in_data = '{"heater":"'+str(seat_heater_id)+'", "level":"0"}'
        cmd_resp = teslaApi.access("REMOTE_SEAT_HEATER_REQUEST", data=str(in_data))
        if cmd_resp == -1:
            msg += "Failed to turn off {} heater for {}!\n".format(
                    seat_heater_str, vehicle_name)
        else:
            msg += "Turning {} heater for {}!\n".format(
                    seat_heater_str, vehicle_name)
    # If no other heater is on, turn off auto conditioning
    data = teslaApi.access("VEHICLE_DATA")
    if data["climate_state"]["seat_heater_left"] == 0 and \
       data["climate_state"]["seat_heater_right"] == 0  and \
       data["climate_state"]["seat_heater_rear_left"] == 0  and \
       data["climate_state"]["seat_heater_rear_center"] == 0  and \
       data["climate_state"]["seat_heater_rear_right"] == 0:
        cmd_resp = teslaApi.access("CLIMATE_OFF")

########################################
#
# Append more vehicle info after user_cmd specific text
#
########################################
# Get current Range info
if charge_rate_units == "mi/hr":
    expected_range = round(325 * battery_level)
    msg += "Current Range: {} miles ({}%, {} mi diff)\n".format(
            battery_range, battery_level, battery_range - expected_range)
else:
    expected_level = round((battery_range/325) * 100)
    msg += "Current Range: {}% ({} mi, {}% diff)\n".format(
            battery_level, battery_range, battery_level - expected_level)

# Get Charging info
if charging_state == "Charging":
    hours = math.floor(time_to_full_charge_in_dec)
    mins = round(60 * (time_to_full_charge_in_dec - hours))
    if charge_rate_units == "mi/hr":
        msg += "{} miles ({}%) added at {} {}\n".format(
                charge_miles_added_rated,
                round((charge_miles_added_rated/325)*100),
                charge_rate,
                charge_rate_units)
    else:
        msg += "{}% ({} miles) added at {} {}\n".format(
                round((charge_miles_added_rated/325)*100),
                charge_miles_added_rated,
                charge_rate,
                charge_rate_units)
    msg += "Time til full charge ({0}%):".format(charge_limit_soc)
    if hours > 0:
        msg += " {} hr".format(hours)
    msg += " {} mins\n".format(mins)
elif charging_state == "Stopped":
    if scheduled_charging_pending == True:
        msg += "Charging will begin {}\n".format(
                time.strftime("%A at %I:%M %p", time.localtime(scheduled_charging_start_time)))
    else:
        msg += "Charging is Stopped\n"

if locked != True:
    msg += "{} is unlocked!\n".format(vehicle_name)

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

if sentry_mode == True:
    msg += "Sentry Mode is active\n"

# List which Seat Heaters may be on
if data["climate_state"]["seat_heater_left"] != 0:
    msg += "Driver's Seat Heater on level {}\n".format(
            data["climate_state"]["seat_heater_left"])
if data["climate_state"]["seat_heater_right"] != 0:
    msg += "Passenger's Seat Heater on level {}\n".format(
            data["climate_state"]["seat_heater_right"])
if data["climate_state"]["seat_heater_rear_left"] != 0:
    msg += "Rear Driver's Seat Heater on level {}\n".format(
            data["climate_state"]["seat_heater_rear_left"])
if data["climate_state"]["seat_heater_rear_center"] != 0:
    msg += "Rear Middle Seat Heater on level {}\n".format(
            data["climate_state"]["seat_heater_center"])
if data["climate_state"]["seat_heater_rear_right"] != 0:
    msg += "Rear Passenger's Seat Heater on level {}\n".format(
            data["climate_state"]["seat_heater_rear_right"])

msg += "{}\n".format(time.strftime("%A @ %I:%M %p", time.localtime()))

########################################
#
# Final joinPush once user_cmd has executed
#
########################################
joinApi.push(SUC_MSG, msg)
