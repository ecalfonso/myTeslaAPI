import joinApi
import math
import teslaApi
import time
import sys

from enum import Enum

BEGIN_T = time.time()

ERR_MSG = "TeslaAPI Failure!"
SUC_MSG = "TeslaAPI"

# Define command Enums
CMD_LIST = "DATA \
        LOCK \
        AC_ON \
        AC_OFF \
        CHARGE_PORT_OPEN \
        CHARGE_PORT_CLOSE \
        CHARGE_START \
        CHARGE_STOP \
        HONK_HORN \
        FLASH_LIGHTS"
CMD = Enum("CMD", CMD_LIST)

# Parse incoming command
user_cmd = sys.argv[1].lower()

if "data" in user_cmd or "status" in user_cmd:
    cmd = CMD.DATA
elif "turn on the ac" in user_cmd or \
        "turn on the air conditioner" in user_cmd or \
        "turn on the fans" in user_cmd or \
        "warm up" in user_cmd:
    cmd = CMD.AC_ON
elif "turn off the ac" in user_cmd or \
        "turn off the air conditioner" in user_cmd or \
        "turn off the fans" in user_cmd or \
        "stop warming up" in user_cmd:
    cmd = CMD.AC_OFF
elif "open the charge port" in user_cmd or \
        "unlock the charge port" in user_cmd or \
        "open the charger port" in user_cmd or \
        "unlock the charger port" in user_cmd:
    cmd = CMD.CHARGE_PORT_OPEN
elif "close the charge port" in user_cmd or \
        "lock the charge port" in user_cmd or \
        "close the charger port" in user_cmd or \
        "lock the charger port" in user_cmd:
    cmd = CMD.CHARGE_PORT_CLOSE
elif "lock the car" in user_cmd or \
        "lock the doors" in user_cmd:
    cmd = CMD.LOCK
elif "start charging" in user_cmd or \
        "begin charging" in user_cmd or \
        "charge now" in user_cmd:
    cmd = CMD.CHARGE_START
elif "stop charging" in user_cmd or \
        "end charging" in user_cmd:
    cmd = CMD.CHARGE_STOP
elif "honk the horn" in user_cmd:
    cmd = CMD.HONK_HORN
elif "flash the lights" in user_cmd:
    cmd = CMD.FLASH_LIGHTS
else:
    print("Unable to process input string: {}".format(user_cmd))
    joinApi.push(ERR_MSG, "Unable to process input string: {}".format(user_cmd))
    exit()

print("Timing: Parsed user_cmd: {}".format(time.time() - BEGIN_T))
BEGIN_T = time.time()


# Wake up car
if teslaApi.carWakeUp() == -1:
    print("Unable to wakeup Tesla!")
    joinApi.push(ERR_MSG, "Unable to wakeup Tesla!")
    exit()

print("Timing: Waking up car: {}".format(time.time() - BEGIN_T))
BEGIN_T = time.time()

# Get initial car data
data = teslaApi.access("VEHICLE_DATA")
if data == -1:
    print("Unable to get Vehicle data!")
    joinApi.push(ERR_MSG, "Unable to get Vehicle data!")
    exit()

print("Timing: Getting vehicle_data: {}".format(time.time() - BEGIN_T))
BEGIN_T = time.time()

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
door_status = data['vehicle_state']['df'] | data['vehicle_state']['pf'] |\
        data['vehicle_state']['dr'] | data['vehicle_state']['pr'] |\
        data['vehicle_state']['ft'] | data['vehicle_state']['rt']
vehicle_name = data['vehicle_state']['vehicle_name']

# Process initial data before executing User command
msg = ""
if cmd == CMD.DATA:
    cmd_resp = data

elif cmd == CMD.AC_ON:
    if data["climate_state"]["is_auto_conditioning_on"] == False:
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
    if data["climate_state"]["is_auto_conditioning_on"] == True:
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

# Append more vehicle info after user_cmd specific text
if charge_rate_units == "mi/hr":
    msg += "Current Range: {0} miles ({1}%)\n".format(battery_range, battery_level)
else:
    msg += "Current Range: {0}% ({1} mi)\n".format(battery_level, battery_range)

if charging_state == "Charging":
    hours = math.floor(time_to_full_charge_in_dec)
    mins = round(60 * (time_to_full_charge_in_dec - hours))
    if charge_rate_units == "mi/hr":
        msg += "{} miles ({}%) added at {} {}\n".format(
                charge_miles_added_rated,
                round((charge_miles_added_rated/310)*100),
                charge_rate,
                charge_rate_units)
    else:
        msg += "{}% ({} miles) added at {} {}\n".format(
                round((charge_miles_added_rated/310)*100),
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

msg += "time: {}\n".format(time.strftime("%H:%M", time.localtime()))

print("Timing: Executing user_cmd: {}".format(time.time() - BEGIN_T))
BEGIN_T = time.time()

# Final joinPush once user_cmd has executed
joinApi.push(SUC_MSG, msg)

print("Timing: Final joinApi.push(): {}".format(time.time() - BEGIN_T))
