from . import config
from . import model
from . import api

from flask import Flask
import os


def create_app(config_class='Production', instance_path=None):
    app = Flask(__name__, instance_path=instance_path, instance_relative_config=True)

    config_class = getattr(config, config_class)
    app.config.from_object(config_class(app))
    try:
        os.makedirs(app.instance_path)
    except FileExistsError:
        pass
    app.config.from_pyfile('config.py', silent=True)

    model.init_app(app)
    api.init_app(app)

    @app.route('/')
    @app.route('/<path:path>')
    def index(path=None):
        return app.send_static_file('index.html')

    return app
