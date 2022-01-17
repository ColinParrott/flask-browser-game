from app import app, socket_io
from config import public, flask_debug, port

if __name__ == '__main__':
    if public:
        socket_io.run(app=app, host='0.0.0.0', port=port, debug=flask_debug)
    else:
        socket_io.run(app=app, port=port, debug=flask_debug)
