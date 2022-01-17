import logging
import random

from pymongo.collection import Collection

from db import db_client
from flask import request, session
from flask_socketio import SocketIO

import config
from trading_cards.packs import packgen

logging.basicConfig(level=config.debug_level,
                    format='[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


class PackOpeningController:

    def __init__(self, socket_io: SocketIO, namespace: str):
        self.socket_io = socket_io
        self.namespace = namespace
        self.users = {}
        self.db_celebs = db_client['sma']['celebs']  # type: Collection
        self.db_cards = db_client['sma']['cards'] if not config.test else db_client['sma']['test_cards']
        self.db_users = db_client['sma']['users'] if not config.test else db_client['sma']['test_users']
        self.all_celebs = list(self.db_celebs.find())
        self.create_handlers()

    def gen_pack(self):
        orig_pack = packgen.gen_pack()
        pack = []

        for p in orig_pack:
            name = p[0]
            rating = p[1]
            rarity = p[2]
            country = self.db_celebs.find_one({'_id': name}, projection={'_id': False, 'country': True})['country']
            self.add_to_card_db(name, rarity, rating, session['discord_id'])
            pack.append({'name': name, 'country': country, 'rarity': rarity, 'rating': rating})

        random.SystemRandom().shuffle(pack)
        return pack

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

    def create_handlers(self):

        @self.socket_io.on('connect', namespace=self.namespace)
        def connect():
            logger.debug('%s connected ' % request.sid)
            self.users[request.sid] = session['discord_id']
            self.socket_io.emit('numPacks', self.get_num_packs(), room=request.sid, namespace=self.namespace)

        @self.socket_io.on('getPack', namespace=self.namespace)
        def get_pack():
            logger.debug('%s getPack()' % request.sid)

            if self.get_num_packs() > 0:
                try:
                    pack = self.gen_pack()
                    self.decrement_pack_count()
                    logger.info(pack)
                    self.socket_io.emit('pack', pack, room=request.sid, namespace=self.namespace)
                except Exception as e:
                    logger.error(e)

        @self.socket_io.on('disconnect', namespace=self.namespace)
        def disconnect():
            logger.debug('%s disconnected ' % request.sid)
            self.users.pop(request.sid)

        @self.socket_io.on('getNumPacks', namespace=self.namespace)
        def send_num_packs():
            self.socket_io.emit('numPacks', self.get_num_packs(), room=request.sid, namespace=self.namespace)

    def decrement_pack_count(self):
        discord_id = int(session['discord_id'])
        self.db_users.find_one_and_update({'_id': discord_id, 'packs_left': {'$gte': 1}},
                                          {'$inc': {'packs_left': -1}})

    def get_num_packs(self):
        discord_id = int(session['discord_id'])
        return int(self.db_users.find_one({'_id': discord_id}, projection={'_id': False, 'packs_left': True})[
                       'packs_left'])
