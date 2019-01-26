#!/bin/sh
if [ -z "$1" ]; then
    env FLASK_ENV=development ./ENV/bin/python3 -m app
else
    env FLASK_ENV=development FLASK_APP="app:create_app('Development')" ./ENV/bin/python3 -m flask "$1"
fi

