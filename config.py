import logging

# Constants
import sys

DB_URI = ""
flask_debug = False
port = 3333 if sys.platform == 'linux' else 3000

# Game variables
test = False if sys.platform == 'linux' else True
public = True
round_time_limit = 35  # seconds
choice_delay = 3 if not test else 0.1  # s
jayden_chance = 15
enable_jayden = True
min_num_players = 2 if not test else 1
min_players_to_earn_packs = 3 if not test else 1

rounds_per_pack = 10

debug_level = logging.DEBUG

images_folder = "app/static/images/"
in_app_images_folder = '/static/images/'

YT_API_KEY = ""
