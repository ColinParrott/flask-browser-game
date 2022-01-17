import logging
import os

from flask import request, session
from flask_socketio import SocketIO

import config
from db.StatsDatabase import StatsDatabase
from stats.obj.CelebStatSet import CelebStatSet
from stats.obj.StatsUser import StatsUser

logging.basicConfig(level=config.debug_level,
                    format='[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


def build_celeb_stats(celeb_dict, person_obj):
    name = person_obj['name']

    if name in celeb_dict:
        person = celeb_dict[name]
    else:
        logger.error('%s not in dict: %s' % (name, celeb_dict.keys()))

    apps = person.apps + 1
    firsts = person.firsts + len(person_obj['first'])
    seconds = person.seconds + len(person_obj['second'])
    thirds = person.thirds + len(person_obj['third'])

    return CelebStatSet(apps, firsts, seconds, thirds)


def add_to_celeb_dict(celeb_dict, person_obj):
    name = person_obj['name']
    stats = build_celeb_stats(celeb_dict, person_obj)
    celeb_dict[name] = stats


def build_user_stats(user_dict, person_obj, discord_id):
    name = person_obj['name']
    person = user_dict[name]

    additional_firsts = 1 if discord_id in [int(x) for x in person_obj['first']] else 0
    additional_seconds = 1 if discord_id in [int(x) for x in person_obj['second']] else 0
    additional_thirds = 1 if discord_id in [int(x) for x in person_obj['third']] else 0

    apps = person.apps + additional_firsts + additional_seconds + additional_thirds
    firsts = person.firsts + additional_firsts
    seconds = person.seconds + additional_seconds
    thirds = person.thirds + additional_thirds

    return CelebStatSet(apps, firsts, seconds, thirds)


def add_to_user_dict(user_dict, person_obj, discord_id):
    name = person_obj['name']
    stats = build_user_stats(user_dict, person_obj, discord_id)
    user_dict[name] = stats


class StatsController:

    def __init__(self, socket_io: SocketIO, namespace: str):
        self.socket_io = socket_io
        self.namespace = namespace
        self.db = StatsDatabase()
        self.users = {}  # type: dict(str, StatsUser)
        self.create_handlers()

    def create_handlers(self):

        @self.socket_io.on('connect', namespace=self.namespace)
        def connect():
            self.users[request.sid] = StatsUser(session['discord_name'], session['discord_id'], session['avatar'])

        @self.socket_io.on('disconnect', namespace=self.namespace)
        def disconnect():
            self.users.pop(request.sid)

        @self.socket_io.on('getPeopleTableStats', namespace=self.namespace)
        def emit_all_celeb_stats():
            logger.debug('getPeopleTableStats()')
            celeb_dict = {}
            total_rounds = self.db.get_number_of_rounds()

            names = [x[:-4] for x in os.listdir(config.images_folder)]

            for name in names:
                celeb_dict[name] = CelebStatSet(0, 0, 0, 0)

            for round in self.db.get_all_rounds():
                add_to_celeb_dict(celeb_dict, round['personOne'])
                add_to_celeb_dict(celeb_dict, round['personTwo'])
                add_to_celeb_dict(celeb_dict, round['personThree'])

            for k, v in celeb_dict.items():
                celeb_dict[k] = v.to_json()

            self.socket_io.emit('peopleTableStats', (celeb_dict, total_rounds), room=request.sid,
                                namespace=self.namespace)

        @self.socket_io.on('getMyStats', namespace=self.namespace)
        def emit_my_stats():
            logger.debug('getMyStats: ' + self.users[request.sid].name)
            self.socket_io.emit('myInfo', (self.users[request.sid].name, self.users[request.sid].avatar),
                                room=request.sid, namespace=self.namespace)

            discord_id = int(self.users[request.sid].discord_id)
            user_dict = self.get_user_stats_dict(discord_id)
            self.socket_io.emit('userStats', (discord_id, user_dict), room=request.sid, namespace=self.namespace)

        @self.socket_io.on('getUsersStats', namespace=self.namespace)
        def get_users_stats(discord_id):
            logger.debug(discord_id)
            discord_id = int(discord_id)
            user_dict = self.get_user_stats_dict(discord_id)

            self.socket_io.emit('userStats', (discord_id, user_dict), room=request.sid, namespace=self.namespace)

        @self.socket_io.on('getMyDiscordID', namespace=self.namespace)
        def get_self_discord_id():
            self.socket_io.emit('myDiscordID', (self.users[request.sid].discord_id), room=request.sid, namespace=self.namespace)

        @self.socket_io.on('getUsers', namespace=self.namespace)
        def get_users():
            users = self.db.get_all_users()

            # Without converting MongoDB Long to str, it rounds the ID up by 1 when sent via the socket
            for i in range(0, len(users)):
                users[i]['_id'] = str(users[i]['_id'])

            self.socket_io.emit('users', users, room=request.sid, namespace=self.namespace)

    def get_user_stats_dict(self, discord_id: int):
        user_dict = {}
        names = [x[:-4] for x in os.listdir(config.images_folder)]

        for name in names:
            user_dict[name] = CelebStatSet(0, 0, 0, 0)

        for r in self.db.get_all_rounds():
            add_to_user_dict(user_dict, r['personOne'], discord_id)
            add_to_user_dict(user_dict, r['personTwo'], discord_id)
            add_to_user_dict(user_dict, r['personThree'], discord_id)

        for k, v in user_dict.items():
            user_dict[k] = v.to_json()

        logger.debug(user_dict)
        return user_dict
