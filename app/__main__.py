from . import create_app, api

app = create_app('Development')
api.socketio.run(app)
