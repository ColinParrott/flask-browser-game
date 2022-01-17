import logging

from flask import session, request

from db import db_client, util
from flask_socketio import SocketIO

import config
from trading_cards.home.TradingCardHome import COST_TO_GEN_CARD
from trading_cards.packs.packgen import gen_crafted_card

logging.basicConfig(level=config.debug_level,
                    format='[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


class CraftingController:
    def __init__(self, socket_io: SocketIO, namespace: str):
        self.socket_io = socket_io
        self.namespace = namespace
        self.users = {}
        self.create_handlers()

        self.db_celebs = db_client['sma']['celebs']
        self.db_users = db_client['sma']['test_users'] if config.test else db_client['sma']['users']
        self.db_cards = db_client['sma']['test_cards'] if config.test else db_client['sma']['cards']

    def add_to_card_db(self, name, rarity, rating, discord_id):
        rating = int(rating)
        discord_id = int(discord_id)
        obj = {
            'name': name,
            'rarity': rarity,
            'rating': rating,
            'owner_id': discord_id
        }
        self.db_cards.insert_one(obj)

    def update_dust_count(self, _id: int, amount: int):
        self.db_users.update_one({'_id': _id}, {'$inc': {'dust': amount}})

    def get_dust_count(self, _id: int):
        res = self.db_users.find_one({'_id': _id}, projection={'_id': 0, 'dust': 1})
        return int(res['dust']) if 'dust' in res else 0

    def create_handlers(self):

        @self.socket_io.on('connect', namespace=self.namespace)
        def connect():
            logging.debug(session['discord_name'] + " connected to crafting.")
            self.socket_io.emit('dustCount', self.get_dust_count(int(session['discord_id'])), room=request.sid, namespace=self.namespace)

        @self.socket_io.on('genCard', namespace=self.namespace)
        def gen_card():

            if self.get_dust_count(int(session['discord_id'])) >= COST_TO_GEN_CARD:
                p = gen_crafted_card()
                logger.info(session['discord_name'] + ' got: ' + str(p))
                full_card = {}
                name = p[0]
                rating = p[1]
                rarity = p[2]
                country = self.db_celebs.find_one({'_id': name}, projection={'_id': False, 'country': True})['country']
                self.add_to_card_db(name, rarity, rating, session['discord_id'])
                full_card['name'] = name
                full_card['country'] = country
                full_card['rarity'] = rarity
                full_card['rating'] = rating
                self.update_dust_count(int(session['discord_id']), -1 * COST_TO_GEN_CARD)
                self.socket_io.emit('generatedCard', (full_card, self.get_dust_count(int(session['discord_id']))), room=request.sid, namespace=self.namespace)
            else:
                self.socket_io.emit('error', "You need at least 100 dust to generate a card.", room=request.sid, namespace=self.namespace)
