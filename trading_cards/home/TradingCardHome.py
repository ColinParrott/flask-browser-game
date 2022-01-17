import logging

from bson import ObjectId
from flask import session, request

from db import db_client, util
from flask_socketio import SocketIO

import config

logging.basicConfig(level=config.debug_level,
                    format='[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

DUST_PER_COMMON = 5
DUST_PER_RARE = 10
DUST_PER_EPIC = 30
DUST_PER_LEGENDARY = 100
COST_TO_GEN_CARD = 100


class TradingCardHome:
    def __init__(self, socket_io: SocketIO, namespace: str):
        self.socket_io = socket_io
        self.namespace = namespace
        self.users = {}
        self.create_handlers()

        self.db_celebs = db_client['sma']['celebs']
        self.db_users = db_client['sma']['test_users'] if config.test else db_client['sma']['users']
        self.db_cards = db_client['sma']['test_cards'] if config.test else db_client['sma']['cards']

    def get_users_cards(self, discord_id):
        discord_id = int(discord_id)
        pipeline = [
            {
                '$lookup':
                    {
                        'from': "celebs",
                        'localField': "name",
                        'foreignField': "_id",
                        'as': "fromCelebs"
                    }
            },
            {
                '$match':
                    {
                        'owner_id': discord_id
                    }
            },
            {
                '$replaceRoot': {'newRoot': {'$mergeObjects': [{'$arrayElemAt': ['$fromCelebs', 0]}, "$$ROOT"]}}
            },
            {
                '$project': {'_id': 1, 'name': 1, 'country': 1, 'rarity': 1, 'rating': 1, 'deleted': 1}
            },
            {
                '$sort': {'rating': -1}
            }
        ]

        return util.JSONEncoder().encode(list(self.db_cards.aggregate(pipeline)))

    def disenchant_cards(self, _id: int, rarity: str):
        result = self.db_cards.delete_many({'owner_id': _id, 'rarity': rarity})
        return result.deleted_count

    def update_dust_count(self, _id: int, amount: int):
        self.db_users.update_one({'_id': _id}, {'$inc': {'dust': amount}})

    def get_dust_count(self, _id: int):
        res = self.db_users.find_one({'_id': _id}, projection={'_id': 0, 'dust': 1})
        return int(res['dust']) if 'dust' in res else 0

    def calculate_dust_generated(self, cards: list):
        leg_count = 0
        epic_count = 0
        rare_count = 0
        common_count = 0

        for c in cards:
            if c['rarity'] == 'legendary':
                leg_count += 1
            elif c['rarity'] == 'epic':
                epic_count += 1
            elif c['rarity'] == 'rare':
                rare_count += 1
            elif c['rarity'] == 'common':
                common_count += 1

        return (leg_count * DUST_PER_LEGENDARY) + (epic_count * DUST_PER_EPIC) + (rare_count * DUST_PER_RARE) + (
                common_count * DUST_PER_COMMON)

    def disenchant_selected(self, discord_id: int, selected_ids: list):
        query = {
            'owner_id': discord_id,
            '$or':
                [
                ],
        }
        for id in selected_ids:
            query['$or'].append({'_id': ObjectId(id)})

        res = self.db_cards.find(query)
        dust_generated = self.calculate_dust_generated(res)

        self.db_cards.delete_many(query)
        return dust_generated

    def create_handlers(self):
        @self.socket_io.on('connect', namespace=self.namespace)
        def connect():
            cards = self.get_users_cards(session['discord_id'])
            num_packs_left = int(self.db_users.find_one({'_id': int(session['discord_id'])})['packs_left'])
            dust_count = self.get_dust_count(int(session['discord_id']))
            name = session['discord_name']
            self.socket_io.emit('connectInfo', (name, num_packs_left, dust_count, cards), room=request.sid,
                                namespace=self.namespace)

        @self.socket_io.on('getDisenchantAllInfo', namespace=self.namespace)
        def get_disenchant_all_info(rarity: str):
            logging.debug('get_disenchant_commons_info')
            num_cards = self.db_cards.find({'owner_id': int(session['discord_id']), 'rarity': rarity}).count()
            dust_per_card = DUST_PER_RARE if rarity == 'rare' else DUST_PER_COMMON
            self.socket_io.emit('disenchantAllInfo', (num_cards, dust_per_card * num_cards, rarity), room=request.sid,
                                namespace=self.namespace)

        @self.socket_io.on('disenchantAll', namespace=self.namespace)
        def disenchant_all_by_rarity(rarity: str):
            discord_id = int(session['discord_id'])
            num_disenchanted = self.disenchant_cards(discord_id, rarity)
            dust_per_card = DUST_PER_RARE if rarity == 'rare' else DUST_PER_COMMON
            self.update_dust_count(discord_id, num_disenchanted * dust_per_card)
            connect()

        @self.socket_io.on('disenchantSelected', namespace=self.namespace)
        def disenchant_selected(card_ids):
            discord_id = int(session['discord_id'])
            logging.info(session['discord_name'] + " wants to discard: " + str(card_ids))
            dust = self.disenchant_selected(discord_id, card_ids)
            self.update_dust_count(discord_id, dust)
            connect()
