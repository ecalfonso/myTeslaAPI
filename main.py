import joinApi
import math
import teslaApi
import time
import sys

from enum import Enum

ERR_MSG = "TeslaAPI Failure!"
SUC_MSG = "TeslaAPI"

# Define command Enums
CMD_LIST = "DATA \
        LOCK \
        AC_ON \
        AC_OFF \
        CHARGE_PORT_OPEN \
        CHARGE_PORT_CLOSE"
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
elif "turn off the ac" in user_cmd and \
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
else:
    print("Unable to process input string: {}".format(user_cmd))
    joinApi.push(ERR_MSG, "Unable to process input string: {}".format(user_cmd))
    exit()

# Wake up car
if teslaApi.carWakeUp() == -1:
    print("Unable to wakeup Tesla!")
    joinApi.push(ERR_MSG, "Unable to wakeup Tesla!")
    exit()

# Get initial car data
data = teslaApi.access("VEHICLE_DATA")

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
    data2 = data

elif cmd == CMD.AC_ON:
    if data["climate_state"]["is_auto_conditioning_on"] == False:
        data2 = teslaApi.access("CLIMATE_ON")
        if data2 == -1:
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
        data2 = teslaApi.access("CLIMATE_OFF")
        if data2 == -1:
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
            data2 = teslaApi.access("CHARGE_PORT_DOOR_CLOSE")
            if data2 == -1:
                msg += "Failed to close Charge Port for {0}!\n".format(vehicle_name)
            else:
                msg += "Closing Charge Port for {0}\n".format(vehicle_name)

elif cmd == CMD.CHARGE_PORT_OPEN:
    if charge_port_door_open == True:
        if charge_port_latch == "Engaged":
            data2 = teslaApi.access("CHARGE_PORT_DOOR_OPEN")
            if data2 == -1:
                msg += "Failed to Unlock Charge Port for {0}!\n".format(vehicle_name)
            else:
                msg += "Unlocking Charge Port for {0}\n".format(vehicle_name)
        else:
            msg += "Charge Port already open for {0}\n".format(vehicle_name)
    else:
        data2 = teslaApi.access("CHARGE_PORT_DOOR_OPEN")
        if data2 == -1:
            msg += "Failed to Open Charge Port for {0}!\n".format(vehicle_name)
        else:
            msg += "Opening Charge Port for {0}\n".format(vehicle_name)

elif cmd == CMD.LOCK:
    if locked == True:
        msg += "{0} is already locked!\n".format(vehicle_name)
    else:
        data2 = teslaApi.access("LOCK")
        if data2 == -1:
            msg += "Failed to lock {0}!\n".format(vehicle_name)
        else:
            msg += "Locking {0}\n".format(vehicle_name)

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

# Final joinPush once user_cmd has executed
joinApi.push(SUC_MSG, msg)
