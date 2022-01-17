import eventlet
eventlet.monkey_patch()

print('hi')
from app import app

if __name__ == '__main__':
    app.run()
