import logging
import math
import os
import time
from threading import Thread

from flask import redirect, url_for, render_template, request
from flask import session
from flask_dance.contrib.discord import make_discord_blueprint, discord
from flask_dance.contrib.spotify import make_spotify_blueprint

import config
from app import app
from app import socket_io
from game.GameController import GameController
from game.spotify import utils as spot_utils
from settings.SettingsController import SettingsController
from stats.StatsController import StatsController
from trading_cards.celebinfo.CelebInfoController import CelebInfoController
from trading_cards.crafting.CraftingController import CraftingController
from trading_cards.home.TradingCardHome import TradingCardHome
from trading_cards.packs.PackOpeningController import PackOpeningController
from trading_cards.packs.packgen import COMMON_CRAFT_CHANCE, RARE_CRAFT_CHANCE, EPIC_CRAFT_CHANCE, \
    LEGENDARY_CRAFT_CHANCE

logging.basicConfig(level=config.debug_level,
                    format='[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# Allows use of HTTP with oauth otherwise it throws an error
if True:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

blueprint = make_discord_blueprint(
    client_id='318897781852995584',
    client_secret='TtxrxbI-1SpoyIAJBVaCmIv9WlJ_cpMR',
    scope=['identify'],
    authorized_url='/'
)
app.register_blueprint(blueprint, url_prefix='/callback')

spotify_blueprint = make_spotify_blueprint(
    client_id='ddfdb221d4454d3eb6d870ad2d0a4664',
    client_secret='f83c448197b24e43ba6ce30299686e5f',
    scope=['user-modify-playback-state', 'user-read-currently-playing'],
    authorized_url='/'
)

app.register_blueprint(spotify_blueprint, url_prefix='/spotifycallback')

game_controller = GameController(socket_io, '/game-space')
stats_controller = StatsController(socket_io, '/stats-space')
settings_controller = SettingsController(socket_io, '/settings-space')
celeb_info_controller = CelebInfoController(socket_io, '/celebinfo-space')
pack_opening_controller = PackOpeningController(socket_io, '/packopening-space')
trading_card_home_controller = TradingCardHome(socket_io, '/tradingcard-space')
crafting_controller = CraftingController(socket_io, '/crafting-space')


def spotify_authorised():
    return spotify_blueprint is not None and spotify_blueprint.token is not None and spotify_blueprint.token[
        'expires_at'] > time.time()


def discord_authorised():
    return blueprint is not None and blueprint.token is not None and blueprint.token[
        'expires_at'] > time.time()

def get_avatar(resp):
    # check user has avatar, otherwise add default discord one (green)
    if resp.json()['avatar'] is not None:
        return "https://cdn.discordapp.com/avatars/" + resp.json()['id'] + "/" + resp.json()['avatar'] + ".png?size=512"
    else:
       return "https://discordapp.com/assets/dd4dbc0016779df1378e7812eabaa04d.png" # default green avatar

@app.route('/index')
@app.route('/')
def index():
    if not discord_authorised():
        session.permanent = True
        return redirect(url_for('discord.login'))
    else:
        resp = discord.get('/api/v6/users/@me')
        assert resp.ok
        logger.debug(resp.json())
        session['discord_id'] = resp.json()['id']
        session['discord_name'] = resp.json()['username'] + "#" + resp.json()['discriminator']
        session['avatar'] = get_avatar(resp)

        logger.info(request.json)
        return render_template('game.html', spotify_auth=spotify_authorised())


@app.route('/stats')
def stats():
    return render_template('stats_table.html')


# @app.after_request
# def add_header(response):
#     # response.cache_control.no_store = True
#     response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
#     response.headers['Pragma'] = 'no-cache'
#     response.headers['Expires'] = '-1'
#     return response


def while_loop_resume(token):
    while not spot_utils.is_playing(token):
        spot_utils.resume_or_pause_track(token, resume=True)

    return


@app.route('/spotify/<action>', methods=['PUT'])
def spotify_pause_or_resume(action):
    # TODO: Add check if token expired and refresh if so (each token lasts  1 hour so probably won't be a problem but still)
    if spotify_authorised():
        logger.debug("Session: " + str(session.values()))
        token = spotify_blueprint.token['access_token']

        if action == 'resume':
            print('resume')
            logger.info('was_playing_before_pause: %s')
            if session.get('was_playing_before_pause', default=False) or session.get('we_paused_spotify',
                                                                                     default=False):
                logger.info('should resume')
                session['we_paused_spotify'] = False
                t = Thread(target=while_loop_resume(token))
                t.start()

        elif action == 'pause':
            print('pause')
            session['was_playing_before_pause'] = spot_utils.is_playing(token)
            if session['was_playing_before_pause']:
                logger.info('should pause')
                session['we_paused_spotify'] = True
                spot_utils.resume_or_pause_track(token, resume=False)

        elif action == 'toggle':
            logger.debug('toggle!')
            spot_utils.resume_or_pause_track(token, resume=not spot_utils.is_playing(token))
    else:
        logger.debug(session['discord_name'] + str(' is not Spotify authorised'))

    return 'done'


@app.route('/mystats')
def my_stats():
    if not discord_authorised():
        return redirect(url_for('discord.login'))
    else:
        resp = discord.get('/api/v6/users/@me')
        assert resp.ok
        session['discord_id'] = resp.json()['id']
        session['discord_name'] = resp.json()['username'] + "#" + resp.json()['discriminator']
        session['avatar'] = get_avatar(resp)
        return render_template('my_stats.html')


@app.route('/playerstats')
def player_stats():
    if not discord_authorised():
        return redirect(url_for('discord.login'))
    else:
        resp = discord.get('/api/v6/users/@me')
        assert resp.ok
        session['discord_id'] = resp.json()['id']
        session['discord_name'] = resp.json()['username'] + "#" + resp.json()['discriminator']
        session['avatar'] = get_avatar(resp)
        return render_template('player_stats.html')


@app.route('/settings')
def settings():
    if not discord_authorised():
        return redirect(url_for('discord.login'))
    else:
        resp = discord.get('/api/v6/users/@me')
        assert resp.ok
        session['discord_id'] = resp.json()['id']
        session['discord_name'] = resp.json()['username'] + "#" + resp.json()['discriminator']
        session['avatar'] = get_avatar(resp)
        return render_template('settings.html')


@app.route('/celebinfo')
def give_celeb_info():
    if not discord_authorised():
        return redirect(url_for('discord.login'))
    else:
        return render_template('celeb_info_giver.html')


@app.route('/tradingcards')
def trading_cards():
    if not discord_authorised():
        return redirect(url_for('discord.login'))
    else:
        return render_template('trading_home.html')


@app.route('/packs')
def packs():
    if not discord_authorised():
        return redirect(url_for('discord.login'))
    else:
        return render_template('packs_NEW.html')


@app.route('/crafting')
def crafting():
    if not discord_authorised():
        return redirect(url_for('discord.login'))
    else:
        return render_template('crafting.html', leg_chance=round(LEGENDARY_CRAFT_CHANCE * 100),
                               epic_chance=round((EPIC_CRAFT_CHANCE - LEGENDARY_CRAFT_CHANCE) * 100),
                               rare_chance=round((RARE_CRAFT_CHANCE - EPIC_CRAFT_CHANCE) * 100),
                               common_chance=round((COMMON_CRAFT_CHANCE) * 100))


@app.route('/linkspotify')
def link_spotify():
    logger.debug('link_spotify()')
    if not spotify_authorised():
        return redirect(url_for('spotify.login'))
    else:
        return redirect('/')


@app.route('/patchnotes')
def patch_notes():
    return render_template('patch_notes.html')
