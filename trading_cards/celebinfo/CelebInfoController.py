import logging
import math
import os
from queue import Queue

from db import db_client
from flask import request, session
from flask_socketio import SocketIO

import config

logging.basicConfig(level=config.debug_level,
                    format='[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


def get_list_of_celebs():
    return [x[:-4] for x in os.listdir(config.images_folder)]


class CelebInfoController:

    def __init__(self, socket_io: SocketIO, namespace: str):
        self.socket_io = socket_io
        self.namespace = namespace
        self.users = {}
        self.queue = Queue()
        self.db_celebs = db_client['sma']['celebs']
        self.populate_db()
        self.populate_queue()
        self.create_handlers()

    def create_handlers(self):
        @self.socket_io.on('connect', namespace=self.namespace)
        def connect():
            self.users[request.sid] = session['discord_id']
            logger.info("%s connected on %s" % (session['discord_name'], self.namespace))
            self.send_celeb()

        @self.socket_io.on('disconnect', namespace=self.namespace)
        def disconnect():
            self.users.pop(request.sid)
            logger.info("%s disconnected on %s" % (session['discord_name'], self.namespace))

        @self.socket_io.on('savePersonInfo', namespace=self.namespace)
        def update_celeb_info(name, iso2_code):
            self.update_celeb(name, iso2_code, self.users[request.sid])
            self.send_celeb()

        @self.socket_io.on('skip', namespace=self.namespace)
        def skip_celeb(name):
            self.queue.put(name)
            self.send_celeb()

    def send_celeb(self):

        num_added = self.get_number_added_by_user(self.users[request.sid])
        packs_earned = math.floor(num_added / 10)

        if not self.queue.empty():
            name = self.queue.get()
            percent = math.floor((num_added % 10) / 10 * 100)
            self.socket_io.emit('receivedPerson', (name, packs_earned, percent), room=request.sid,
                                namespace=self.namespace)
        else:
            self.socket_io.emit('noMoreLeft', packs_earned, room=request.sid, namespace=self.namespace)

    def populate_queue(self):
        for name in self.get_list_of_celebs_without_country():
            self.queue.put(name)

    def get_number_added_by_user(self, discord_id):
        discord_id = int(discord_id)
        return int(self.db_celebs.count(
            {
                '$and':
                    [
                        {'modifier': discord_id},
                        {'country':
                            {
                                '$exists': True
                            }
                        }
                    ]

            }
        ))

    def update_celeb(self, name, country_code, discord_id):
        logger.debug('update_celeb()')
        discord_id = int(discord_id)
        logger.debug('name: %s \t country_code: %s \t discord_id: %d' % (name, country_code, discord_id))
        self.db_celebs.update_one(
            {
                '_id': name
            },
            {
                '$set':
                    {
                        'country': country_code,
                        'modifier': discord_id
                    }
            }
        )

    def get_list_of_celebs_without_country(self):
        result = list(self.db_celebs.find({
            'country':
                {
                    '$exists': False
                }
        }))

        return [r['_id'] for r in result]

    def populate_db(self):
        for name in get_list_of_celebs():
            self.db_celebs.update_one(
                {
                    '_id': name
                },
                {
                    '$set':
                        {
                            '_id': name
                        }
                },
                upsert=True
            )
