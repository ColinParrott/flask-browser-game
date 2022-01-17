import logging
import math
import os
import random
from typing import List, Dict

import eventlet
from flask import session, request
from flask_socketio import SocketIO

import config
import numpy as np
from db.GameDatabase import GameDatabase
from game import jayden_helper
from game.obj.Celebrity import Celebrity
from game.obj.Player import Player
from game.obj.Round import Round

# init logger
from game.obj.consts.Choice import Choice

logging.basicConfig(level=config.debug_level,
                    format='[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# hide other modules debug logs
logging.getLogger("requests_oauthlib").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def valid_username(name: str, player_names: List):
    if len(name.strip()) <= 0:
        return False, 'Username can\'t be empty!'
    elif name in player_names:
        return False, 'Username is already taken!'
    else:
        return True, ''


def is_clean_sweep(players: Dict[str, Player]):
    c1 = None
    c2 = None
    c3 = None

    for v in players.values():
        if v.chosen:
            c1 = v.choices[0]
            c2 = v.choices[1]
            c3 = v.choices[2]
            break

    for v in players.values():
        if v.chosen:
            if c1 != v.choices[0] or c2 != v.choices[1] or c3 != v.choices[2]:
                return False

    return True


class GameController:

    def __init__(self, socket_io: SocketIO, namespace: str, players: dict = {}):
        self.socket_io = socket_io
        self.namespace = namespace
        self.create_handlers()
        self.players = players
        self.round_started = False
        self.round_num = 1
        self.round = Round(self.round_num)
        self.in_game = False
        self.round_timer = 0
        self.game_db = GameDatabase()
        self.number_submitted = 0

    def start_round(self):
        self.in_game = True
        self.round_timer = 0
        self.socket_io.emit('toggleStartButton', 1, namespace=self.namespace)
        self.setup_round()

    def setup_round(self):
        logger.debug('setup_round()')

        jayden_info = None
        is_jayden = False
        pics = []

        if config.enable_jayden:
            jayden_num = random.SystemRandom().randint(1, config.jayden_chance)
            is_jayden = jayden_num == 1
            if is_jayden == 1:
                pics, jayden_info = self.generate_jayden_info()
                logger.info('JAYDEN ROUND')
        else:
            logger.warning('Jayden rounds disabled in config')

        if not is_jayden:
            all_pics = os.listdir(config.images_folder)
            pic_indices = random.SystemRandom().sample(range(0, len(all_pics)), 3)

            for i in pic_indices:
                pics.append(all_pics[i])

        logger.info('Chosen pictures: ' + str(pics))

        celebs = []
        for i in range(0, 3):
            celebs.append(Celebrity(name=pics[i][:-4], url=pics[i]))

        self.round = Round(num=self.round_num, celebs=celebs, is_jayden=is_jayden, jayden_info=jayden_info)
        self.round_started = True

        self.socket_io.emit('updateRound', (
            self.round.to_json(), config.in_app_images_folder, [x.to_json() for x in self.players.values()]),
                            namespace=self.namespace)

    def send_updated_names(self):
        self.socket_io.emit('usernameUpdated', ([x.to_json() for x in self.players.values()], self.round_started),
                            namespace=self.namespace)

    def generate_jayden_info(self):
        logger.debug('generate jayden_info')
        chosen_id = random.SystemRandom().choice([x.discord_id for x in self.players.values()])
        logger.debug('chosen_id: %s' % chosen_id)
        stat = Choice.SECOND if random.SystemRandom().randint(1, 2) == 1 else Choice.THIRD

        chosen_name = None
        for key in self.players.keys():
            if self.players[key].discord_id == chosen_id:
                chosen_name = self.players[key].discord_name
                break

        return jayden_helper.jayden_round(int(chosen_id), stat, chosen_name)

    def create_handlers(self):
        @self.socket_io.on('disconnect', namespace=self.namespace)
        def disconnect():
            logger.info('%s disconnected on %s/%s' % (session['discord_name'], self.namespace, request.sid))
            self.players.pop(request.sid)
            self.socket_io.emit('usernameUpdated', ([x.to_json() for x in self.players.values()], self.round_started),
                                namespace=self.namespace)

            # TODO: FIX AND RE-ENABLE
            # self.check_if_round_end()

        @self.socket_io.on('connect', namespace=self.namespace)
        def connect():
            import pprint
            pprint.pprint(session)
            logger.info('%s connected on %s/%s' % (session['discord_name'], self.namespace, request.sid))
            self.players[request.sid] = Player(discord_name=session['discord_name'], discord_id=session['discord_id'],
                                               nickname=session['discord_name'], choices=[])

            logger.debug('Connected: ' + str([str(self.players[x]) for x in self.players.keys()]))

            self.game_db.register_user(self.players[request.sid])
            self.send_updated_names()

            if self.round_started:
                self.socket_io.emit('updateRound', (
                    self.round.to_json(), config.in_app_images_folder, [x.to_json() for x in self.players.values()]),
                                    room=request.sid, namespace=self.namespace)

            if self.in_game:
                self.socket_io.emit('updateStatusText', 'Round in progress', room=request.sid, namespace=self.namespace)

        @self.socket_io.on('updateUsername', namespace=self.namespace)
        def on_update_username(new_name):
            logger.info('%s requested to change their name to: %s' % (self.players[request.sid].nickname, new_name))

            valid, error_msg = valid_username(new_name, [x.nickname for x in self.players.values()])
            self.socket_io.emit('isValidUsername', (valid, error_msg), namespace=self.namespace, room=request.sid)

            if valid:
                old_name = self.players[request.sid].nickname
                self.players[request.sid].nickname = new_name
                session['nickname'] = new_name
                logger.info('%s changed username to: %s' % (old_name, new_name))
                self.send_updated_names()

        @self.socket_io.on('finalAnswers', namespace=self.namespace)
        def on_final_answers(choice_one, choice_two, choice_three):
            logger.debug('finalAnswers')
            self.number_submitted += 1

            if self.number_submitted == 1:
                self.socket_io.start_background_task(target=self.round_timer_thread)

            # TODO: Change to array in client-side so this can be simpler
            self.players[request.sid].choices.append(choice_one)
            self.players[request.sid].choices.append(choice_two)
            self.players[request.sid].choices.append(choice_three)

            self.players[request.sid].chosen = True
            self.send_updated_names()

            self.check_if_round_end()

        @self.socket_io.on('checkRoundStarted', namespace=self.namespace)
        def check_round_started():
            logger.debug('checkRoundStarted')
            if self.round_started:
                self.socket_io.emit('roundHasStarted', room=request.sid, namespace=self.namespace)
            else:
                self.socket_io.emit('alert', 'Round has not been started yet', room=request.sid,
                                    namespace=self.namespace)

        @self.socket_io.on('gameStartRequested', namespace=self.namespace)
        def on_game_start_request():
            if config.min_num_players < 2:
                logger.warning('Minimum number of players set to less than 2 (%d)' % config.min_num_players)
            if not self.in_game:
                logger.debug('Game start request received from %s' % (self.players[request.sid].nickname))
                if len(self.players) >= config.min_num_players:
                    self.start_round()
                else:
                    logger.debug('Won\'t start game with less than 2 players')

    def round_timer_thread(self):
        while True:
            self.socket_io.emit('updateStatusText', str(config.round_time_limit - self.round_timer),
                                namespace=self.namespace)
            self.round_timer += 1
            eventlet.sleep(1)
            if self.round_timer >= config.round_time_limit:
                self.round_timer = 0
                self.end_round()
                return
            elif not self.round_started:
                self.round_timer = 0
                return

    def show_choices(self):
        self.socket_io.emit('endRound', ([x.to_json() for x in self.players.values()], self.round.to_json()),
                            namespace=self.namespace)

        choices = [str(Choice.FIRST), str(Choice.SECOND), str(Choice.THIRD)]

        for c in choices:
            eventlet.sleep(config.choice_delay)
            self.socket_io.emit('updateStatusText', c.upper() + ' CHOICES', namespace=self.namespace)
            logger.debug([x.to_json() for x in self.players.values()])
            self.socket_io.emit('showChoices', (c, [x.to_json() for x in self.players.values()]),
                                namespace=self.namespace)

        if is_clean_sweep(self.players):
            if config.test or len(
                    np.unique([p.discord_id for p in self.players.values()])) >= config.min_players_to_earn_packs:
                logger.info('GIVE SWEEP PACK')
                self.give_pack_to_random_player()

            logger.info('clean sweep')
            self.socket_io.emit('playAudio', ('sweep.mp3', 0.1), namespace=self.namespace)

        eventlet.sleep(config.choice_delay)
        self.socket_io.emit('clearChoices', namespace=self.namespace)
        self.create_new_round()

    def give_pack_to_random_player(self):
        player_key = random.SystemRandom().choice(list(self.players.keys()))
        player = self.players[player_key]  # type: Player
        num_packs_left = self.game_db.get_num_packs(discord_id=player.discord_id)
        self.game_db.give_player_pack(player.discord_id)
        self.socket_io.emit('updatePackCounter', num_packs_left, room=player_key, namespace=self.namespace)
        self.socket_io.emit('sweepPack', player.nickname, namespace=self.namespace)

    def end_round(self):
        logger.info('end_round()')
        self.round_started = False
        self.game_db.store_round(self.round, self.players)

        if len(np.unique([p.discord_id for p in self.players.values()])) >= config.min_players_to_earn_packs:
            players_due_pack = self.game_db.decrement_pack_counts_and_get_users_due_packs(
                np.unique([int(p.discord_id) for p in self.players.values()]))
            logger.info('Players due pack: %s' % players_due_pack)
            for u in self.game_db.get_pack_progress_with_ids():
                self.send_pack_progress(u['_id'], u['rounds_to_pack'], u['packs_left'])

        self.socket_io.start_background_task(self.show_choices)

    def send_pack_progress(self, discord_id, rounds_left, packs):
        logger.debug('send_pack_progress()')
        progress = math.floor(((config.rounds_per_pack - rounds_left) / config.rounds_per_pack) * 100)

        # TODO: Reverse so db returns list of all people, then searches our local player list
        for k, v in self.players.items():
            if int(v.discord_id) == int(discord_id):
                socket_id = k
                logger.debug(socket_id)
                self.socket_io.emit('packRoundProgress', (progress, packs), room=socket_id, namespace=self.namespace)
                break

    def create_new_round(self):
        self.reset_players()
        self.send_updated_names()
        self.start_round()

    def reset_players(self):
        logger.debug('reset_players()')
        self.number_submitted = 0
        for k in self.players.keys():
            self.players[k].chosen = False
            self.players[k].choices = []

    def check_if_round_end(self):
        if len(self.players) > 0:
            all_chosen = True

            for key in self.players.keys():
                if not self.players[key].chosen:
                    all_chosen = False
                    break

            if all_chosen:
                logger.debug('all chosen')
                self.end_round()
