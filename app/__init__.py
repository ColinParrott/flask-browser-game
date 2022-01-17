from datetime import timedelta

from flask import Flask
from flask_socketio import SocketIO
from werkzeug.contrib.fixers import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.secret_key = 'catkeyboard'
app.config['TEMPLATES_AUTO_RELOAD'] = True
# app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)
# app.config['SESSION_COOKIE_SECURE'] = True

# app.config['SERVER_NAME'] = config.SERVER_NAME
# app.config['SESSION_COOKIE_DOMAIN'] = config.SERVER_NAME
socket_io = SocketIO(app)

from app import routes
