import requests

from config import YT_API_KEY

BASE_URL = "https://www.googleapis.com/youtube/v3/videos?part=id&id=%s&key=" + YT_API_KEY


def valid_video_id(video_id: str):
    target_url = BASE_URL % video_id

    json = requests.get(target_url).json()

    if 'items' in json:
        if len(json['items']) == 1:
            return True

    return False
