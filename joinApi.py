import json
import requests
import urllib.parse

from pathlib import Path

def push(title, text):
    # Define Join config file
    join_config_file = 'join_config.json'

    JOIN_API_URL = 	"https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush?"
    JOIN_DEV_ID = 	"deviceId={}"
    JOIN_API_KEY = 	"&apikey={}"
    JOIN_TITLE = 	"&title={}"
    JOIN_TEXT = 	"&text={}"

    # Check that join_config.json exists
    if not Path(join_config_file).is_file():
        print("Missing {}!".format(join_config_file))
        return 1

    # Get config data
    join_cfg = json.load(open(join_config_file))
    apikey = join_cfg['apikey']
    deviceId = join_cfg['deviceId']

    # Build Join Request
    url = \
        JOIN_API_URL + \
        JOIN_DEV_ID.format(deviceId) + \
        JOIN_API_KEY.format(apikey) + \
        JOIN_TITLE.format(urllib.parse.quote(title)) + \
        JOIN_TEXT.format(urllib.parse.quote(text))

    # Make Join request
    requests.get(url)
    return 0
