import logging
from typing import Dict

from pymongo.collection import Collection

import config
from db import db_client
from game.obj.Player import Player
from game.obj.Round import Round
from game.obj.consts.Choice import Choice

logging.basicConfig(level=config.debug_level,
                    format='[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


def get_choice_array(image_num: int, choice: Choice, players: Dict[str, Player]):
    result = []

    for v in players.values():
        if v.chosen and v.choices[image_num - 1] == str(choice):
            result.append(int(v.discord_id))

    return result


class GameDatabase:

    def __init__(self):
        self.client = db_client

        if not config.test:
            self.db_rounds = self.client['sma']['rounds']  # type: Collection
            self.db_users = self.client['sma']['users']  # type: Collection
        else:
            self.db_rounds = self.client['sma']['test_rounds']  # type: Collection
            self.db_users = self.client['sma']['test_users']  # type: Collection

    def register_user(self, player: Player):
        query = {'_id': int(player.discord_id)}
        update = {
            '$set':
                {
                    '_id': int(player.discord_id),
                    'name': player.discord_name
                }
        }
        old = self.db_users.find_one_and_update(query, update, upsert=True)

        if old is None:
            self.db_users.update_one(query, {'$set': {'rounds_to_pack': int(config.rounds_per_pack), 'packs_left': 5}})

    def store_round(self, round: Round, players: Dict[str, Player]):
        logger.debug('store_round()')
        json_round = {
            'personOne':
                {
                    'name': round.celebs[0].name,
                    'first': get_choice_array(1, Choice.FIRST, players),
                    'second': get_choice_array(1, Choice.SECOND, players),
                    'third': get_choice_array(1, Choice.THIRD, players)
                },
            'personTwo':
                {
                    'name': round.celebs[1].name,
                    'first': get_choice_array(2, Choice.FIRST, players),
                    'second': get_choice_array(2, Choice.SECOND, players),
                    'third': get_choice_array(2, Choice.THIRD, players)
                },
            'personThree':
                {
                    'name': round.celebs[2].name,
                    'first': get_choice_array(3, Choice.FIRST, players),
                    'second': get_choice_array(3, Choice.SECOND, players),
                    'third': get_choice_array(3, Choice.THIRD, players)
                }
        }

        self.db_rounds.insert_one(json_round)
        logger.debug('json_round: ' + str(json_round))

    def decrement_pack_counts_and_get_users_due_packs(self, users):
        users = [int(u) for u in users]

        for u in users:
            self.db_users.update_one({'_id': u, 'rounds_to_pack': {'$gte': 1}}, {'$inc': {'rounds_to_pack': -1}, })

        return self.get_users_due_pack()

    def get_users_due_pack(self):
        users_due_pack = [x['_id'] for x in list(self.db_users.find({'rounds_to_pack': 0}, projection=['_id']))]
        self.db_users.update_many({'rounds_to_pack': 0},
                                  {'$set': {'rounds_to_pack': config.rounds_per_pack}, '$inc': {'packs_left': 1}})
        return users_due_pack

    def get_num_packs(self, discord_id):
        discord_id = int(discord_id)
        return int(self.db_users.find_one({'_id': int(discord_id)})['packs_left'])

    def get_pack_progress_with_ids(self):
        return list(self.db_users.find(projection=['_id', 'rounds_to_pack', 'packs_left']))

    def give_player_pack(self, discord_id):
        discord_id = int(discord_id)
        self.db_users.find_one_and_update({'_id': discord_id}, {'$inc': {'packs_left': 1}})
