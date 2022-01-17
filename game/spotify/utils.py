import logging
import math
import time
from base64 import b64encode

import requests

import config

pause_url = 'https://api.spotify.com/v1/me/player/pause'
play_url = 'https://api.spotify.com/v1/me/player/play'
status_url = 'https://api.spotify.com/v1/me/player/currently-playing'

logging.basicConfig(level=config.debug_level,
                    format='[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

BASE_REFRESH_URL = "https://accounts.spotify.com/api/token"
COMBINED_AUTH = b'ddfdb221d4454d3eb6d870ad2d0a4664:f83c448197b24e43ba6ce30299686e5f'


def get_refreshed_token(token):
    headers = \
        {
            'Authorization': b"Basic " + b64encode(COMBINED_AUTH)
        }

    body = {
        'grant_type': 'refresh_token',
        'refresh_token': token
    }

    res = requests.post(url=BASE_REFRESH_URL, data=body, headers=headers)
    logger.debug("JSON: " + str(res.json()))
    json = res.json()
    json['expires_at'] = math.floor(time.time() + res.json()['expires_in'])
    return json


def gen_headers(token: str):
    return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
    }


def is_playing(access_token: str):
    logger.debug('is_playing()')
    r = requests.get(url=status_url, headers=gen_headers(access_token))

    # Weird spotify API operation, sometimes returns 204 if nothing playing
    if r.status_code == 204:
        return False

    logger.debug(r.json())
    if 'is_playing' in r.json():
        return r.json()['is_playing']
    else:
        return False


def resume_or_pause_track(access_token: str, resume: bool):
    logger.debug('resume_or_pause_track()')
    r = requests.put(
        url=play_url if resume else pause_url,
        headers=gen_headers(access_token)
    )

    logger.debug(r.text)
