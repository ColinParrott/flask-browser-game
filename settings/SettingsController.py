import logging

from flask import session, request
from flask_socketio import SocketIO

import config
from db.SettingsDatabase import SettingsDatabase
from game.obj.consts import Choice
from settings.util import valid_video_id

logging.basicConfig(level=config.debug_level,
                    format='[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


class SettingsController:

    def __init__(self, socket_io: SocketIO, namespace: str):
        self.socket_io = socket_io
        self.namespace = namespace
        self.db = SettingsDatabase()
        self.create_handlers()

    def create_handlers(self):

        @self.socket_io.on('getJaydenSong', namespace=self.namespace)
        def get_jayden_song(choice: str):
            result = self.db.get_jayden_settings(session['discord_id'], Choice.to_enum(choice))
            self.socket_io.emit('jaydenSong', (choice, result), room=request.sid, namespace=self.namespace)

        @self.socket_io.on('setJaydenSong', namespace=self.namespace)
        def set_jayden_song(video_id: str, start: int, choice: str):
            logger.debug('set_jayden_song()')
            if valid_video_id(video_id):
                logger.debug('valid: %s' % video_id)
                self.db.save_jayden_settings(session['discord_id'], video_id, start, Choice.to_enum(choice))
                result = self.db.get_jayden_settings(session['discord_id'], Choice.to_enum(choice))
                self.socket_io.emit('jaydenSong', (choice, result, True), room=request.sid, namespace=self.namespace)
            else:
                logger.debug('invalid: %s' % video_id)
                self.socket_io.emit('invalidVideoId', choice, room=request.sid, namespace=self.namespace)
