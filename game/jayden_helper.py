from pymongo import MongoClient

from game.obj.JaydenInfo import JaydenInfo
from game.obj.consts.Choice import Choice

DB_URI = 'mongodb+srv://admin:lUmhMSFylna8eEzR@cluster0-cklle.mongodb.net/sma'
client = MongoClient(DB_URI)

JAYDEN_MIN_APPEARANCES = 6
MIN_COMMON_PEOPLE = 10

rounds = client['sma']['rounds']
users = client['sma']['users']


def add_count(stat: str, user_id: int, round_obj):
    if user_id in round_obj[stat]:
        return 1
    else:
        return 0


def add_to_dict(people_dict: dict, user_id: int, round_obj):
    name = round_obj['name']

    if name not in people_dict: people_dict[name] = {'first': 0, 'second': 0, 'third': 0, 'app': 0}

    new_firsts = people_dict[name]['first'] + add_count('first', user_id, round_obj)
    new_seconds = people_dict[name]['second'] + add_count('second', user_id, round_obj)
    new_thirds = people_dict[name]['third'] + add_count('third', user_id, round_obj)
    new_apps = new_firsts + new_seconds + new_thirds

    people_dict[name] = {'first': new_firsts, 'second': new_seconds, 'third': new_thirds, 'app': new_apps}


def has_at_least_x_common_people(people_dict: dict):
    common_count = 0
    for _, stats in people_dict.items():
        if stats['app'] >= JAYDEN_MIN_APPEARANCES:
            common_count += 1

        if common_count >= MIN_COMMON_PEOPLE:
            return True

    return False


def get_video_and_time(user_id: int, stat: Choice):
    stat = str(stat)
    stat_str = 'jayden_' + stat
    video_str = stat_str + '.video_id'
    time_str = stat_str + '.start_time'

    res = users.find_one({'_id': int(user_id)}, projection={'_id': False, video_str: True, time_str: True})

    if stat_str in res:
        if 'video_id' in res[stat_str] and 'start_time' in res[stat_str]:
            video_id = res[stat_str]['video_id']
            start_time = res[stat_str]['start_time']
            return video_id, start_time

    return None, None


def jayden_round(user_id: int, stat: Choice, nickname: str):
    video_id, start_time = get_video_and_time(user_id, stat)
    people_dict = {}  # {person_name: {first: x, second: x, third: x, app: 0}}
    rounds_obj = rounds.find()
    for r in rounds_obj:
        add_to_dict(people_dict, user_id, r['personOne'])
        add_to_dict(people_dict, user_id, r['personTwo'])
        add_to_dict(people_dict, user_id, r['personThree'])

    # Remove those who have appeared too few times
    # and add percentages
    has_3_people = has_at_least_x_common_people(people_dict)
    for name, stats in people_dict.copy().items():
        if stats['app'] < JAYDEN_MIN_APPEARANCES and has_3_people:
            people_dict.pop(name)
        else:
            app = people_dict[name]['app']
            people_dict[name]['first_per'] = (people_dict[name]['first'] / app) if app > 0 else 0
            people_dict[name]['second_per'] = (people_dict[name]['second'] / app) if app > 0 else 0
            people_dict[name]['third_per'] = (people_dict[name]['third'] / app) if app > 0 else 0

    client.close()

    stat_str = str(stat)
    people_list = [(name, people_dict[name]) for name in people_dict.keys()]
    sorted_people = sorted(people_list, key=lambda x: (-x[1][stat_str + '_per'], -x[1][stat_str]))

    pics = []
    for i in range(0, 3):
        pics.append(sorted_people[i][0] + '.png')

    return pics, JaydenInfo(username=nickname, stat=stat, video_id=video_id, start_time=start_time)
