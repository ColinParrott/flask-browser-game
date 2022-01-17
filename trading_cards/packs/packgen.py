import logging
import math
import os
import random
from collections import OrderedDict

from pymongo import MongoClient

import config
from stats.obj.CelebStatSet import CelebStatSet

db_client = MongoClient(config.DB_URI)
db_celebs = db_client['sma']['celebs']  # type: Collection
db_rounds = db_client['sma']['rounds']  # type: Collection

logging.basicConfig(level=config.debug_level,
                    format='[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


def get_list_of_celebs():
    return [x[:-4] for x in os.listdir(config.images_folder)]


def build_celeb_stats(celeb_dict, person_obj):
    name = person_obj['name']

    if name in celeb_dict:
        person = celeb_dict[name]
    else:
        print('%s not in dict: %s' % (name.encode('utf-8'), celeb_dict.keys()))

    apps = person.apps + 1
    firsts = person.firsts + len(person_obj['first'])
    seconds = person.seconds + len(person_obj['second'])
    thirds = person.thirds + len(person_obj['third'])

    return CelebStatSet(apps, firsts, seconds, thirds)


def add_to_celeb_dict(celeb_dict, person_obj):
    name = person_obj['name']
    stats = build_celeb_stats(celeb_dict, person_obj)
    celeb_dict[name] = stats


def normalise_scores(scores):
    max_out = 100
    min_out = 20
    normalised = []
    max_score = max([y[1] for y in scores])
    min_score = min([y[1] for y in scores])

    for s in scores:
        b_minus_a = (max_out - min_out)
        frac = (s[1] - min_score) / (max_score - min_score)
        norm_score = b_minus_a * frac + min_out
        normalised.append((s[0], math.floor(norm_score)))

    return normalised


def percent(num, total):
    return (num / total) * 100


def calculate_score(apps, total_choices, firsts, seconds, thirds):
    second_score = percent(seconds, total_choices) * (1 + math.log(seconds + 1))
    first_score = percent(firsts, total_choices) * (1 + math.log(firsts + 1))
    third_score = percent(thirds, total_choices) * (2 + math.log(thirds + 50))
    return (3 * second_score) + (1.5 * first_score) - (0.1 * third_score)


def get_score_list():
    celeb_dict = {}
    for name in get_list_of_celebs():
        celeb_dict[name] = CelebStatSet(0, 0, 0, 0)

    for round in db_rounds.find():
        add_to_celeb_dict(celeb_dict, round['personOne'])
        add_to_celeb_dict(celeb_dict, round['personTwo'])
        add_to_celeb_dict(celeb_dict, round['personThree'])

    scores = []
    for k, v in celeb_dict.items():
        if v.apps >= 5:
            total_choices = v.firsts + v.seconds + v.thirds
            score = calculate_score(v.apps, total_choices, v.firsts, v.seconds, v.thirds)
            scores.append((k, score))

    scores = sorted(scores, key=lambda x: -x[1])
    return normalise_scores(scores)


def gen_rarity():
    rand = random.SystemRandom().random()

    if rand <= LEGENDARY_CHANCE:
        return 'legendary'
    elif rand <= EPIC_CHANCE:
        return 'epic'
    elif rand <= RARE_CHANCE:
        return 'rare'
    else:
        return 'common'


def gen_pack_rarities():
    pack = []
    for _ in range(4):
        pack.append(gen_rarity())

    if all(r == 'common' for r in pack):
        pack[random.SystemRandom().randint(0, 3)] = 'rare'

    return pack


def populate_rarity_arrays():
    for s in scores:
        if s[1] >= LEGENDARY_BOUNDS[0]:
            legendaries.append((s[0], s[1], 'legendary'))
        elif s[1] >= EPIC_BOUNDS[0]:
            epics.append((s[0], s[1], 'epic'))
        elif s[1] >= RARE_BOUNDS[0]:
            rares.append((s[0], s[1], 'rare'))
        else:
            commons.append((s[0], s[1], 'common'))


def gen_pack():
    db_celebs = db_client['sma']['celebs']  # type: Collection
    db_rounds = db_client['sma']['rounds']  # type: Collection
    pack = []
    rarities = gen_pack_rarities()

    for r in rarities:
        if r == 'common':
            pack.append(random.SystemRandom().choice(commons))
        elif r == 'rare':
            pack.append(random.SystemRandom().choice(rares))
        elif r == 'epic':
            pack.append(random.SystemRandom().choice(epics))
        else:
            pack.append(random.SystemRandom().choice(legendaries))

    return pack


def gen_crafted_card():
    rand = random.SystemRandom().random()

    logging.debug('Crafted rand: %f' % rand)

    if rand <= LEGENDARY_CRAFT_CHANCE:
        return random.SystemRandom().choice(legendaries)
    elif rand <= EPIC_CRAFT_CHANCE:
        return random.SystemRandom().choice(epics)
    elif rand <= RARE_CRAFT_CHANCE:
        return random.SystemRandom().choice(rares)
    else:
        return random.SystemRandom().choice(commons)


def test_pack_drop_rate(iterations: int):
    outcomes = OrderedDict()
    for r in rarities:
        outcomes[r] = 0

    for _ in range(iterations):
        pack = gen_pack_rarities()
        for r in rarities:
            outcomes[r] += 1 if r in pack else 0

    for k, v in outcomes.items():
        print("%s: %.3f%%" % (k, v / iterations * 100))


legendaries = []
epics = []
rares = []
commons = []
rarities = ['legendary', 'epic', 'rare', 'common']

LEGENDARY_BOUNDS = (90, 100)
EPIC_BOUNDS = (80, LEGENDARY_BOUNDS[0] - 1)
RARE_BOUNDS = (70, EPIC_BOUNDS[0] - 1)
COMMON_BOUNDS = (20, RARE_BOUNDS[0] - 1)

LEGENDARY_CHANCE = 0.0055
EPIC_CHANCE = 0.055
RARE_CHANCE = 0.20
COMMON_CHANCE = 1 - RARE_CHANCE

LEGENDARY_CRAFT_CHANCE = 0.04
EPIC_CRAFT_CHANCE = 0.22
RARE_CRAFT_CHANCE = 0.55
COMMON_CRAFT_CHANCE = 1 - RARE_CRAFT_CHANCE

scores = get_score_list()
raw_scores = [x[1] for x in scores]
populate_rarity_arrays()

if __name__ == '__main__':
    test_pack_drop_rate(1000000)
    db_client.close()
