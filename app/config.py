import os.path


class Base(object):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    def __init__(self, app):
        pass

class Development(Base):
    DEBUG = True

    def __init__(self, app):
        self.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(app.instance_path, 'db.sqlite3')
        self.SQLALCHEMY_ECHO = True

class Production(Base):
    def __init__(self, app):
        self.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(app.instance_path, 'db.sqlite3')
