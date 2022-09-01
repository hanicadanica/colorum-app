from flask_jwt_extended import JWTManager
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from requests.auth import HTTPBasicAuth
from socketio import Client
from requests import post
from flask import Flask
import atexit
import logging
from flask.logging import default_handler
from logging.handlers import RotatingFileHandler

# socketio connection to northbound server
northbound_connection = Client()

# northbound client credentials
northbound_access_token = None
northbound_refresh_token = None

# database
db = SQLAlchemy()

# list containing dictionaries of the colorum vehicles
all_colorum_vehicles = None

# list that contains the available routes coming from the Northbound Interface for the Colorum app to use
available_routes = None


def create_server(config_type="config.DevelopmentConfig"):
    # create flask app
    app = Flask(__name__)

    # configure app
    app.config.from_object(config_type)

    # enable logging to file
    configure_logging(app)

    # register blueprints
    register_blueprints(app)

    # set program to emit a stop device stream upon exit
    atexit.register(disconnect_from_northbound)

    # initialize JWT and CORS
    jwt = JWTManager(app)
    cors = CORS(app, resources={r"/*": {"origins": "*"}})

    # initialize sqlalchemy
    from app.models import GPSDevice, Route, ColorumAdmin, ColorumUser

    db.init_app(app)
    migrate = Migrate(app, db, compare_type=True)

    # connect to the northbound server
    if app.config["NORTHBOUND_USERNAME"] and app.config["NORTHBOUND_PASSWORD"]:
        connect_to_northbound(app)

        # send the start stream event to the northbound server
        northbound_connection.emit("start_device_location_stream")

    return app


# function to connect to the northbound platform via login and socketio connect with token
def connect_to_northbound(app):
    # send login request to northbound platform
    northbound_url = "http://%s:%s" % (
        app.config["NORTHBOUND_ADDRESS"],
        app.config["NORTHBOUND_PORT"],
    )
    northbound_login_url = "%s/login/" % (northbound_url,)
    northbound_login = post(
        northbound_login_url,
        auth=HTTPBasicAuth(
            app.config["NORTHBOUND_USERNAME"], app.config["NORTHBOUND_PASSWORD"]
        ),
    )

    # get access and refresh tokens from request response
    global northbound_access_token, northbound_refresh_token
    northbound_response_json = northbound_login.json()
    northbound_access_token = northbound_response_json["access_token"]
    northbound_refresh_token = northbound_response_json["refresh_token"]

    # connect to the northbound platform using socketio connect
    global northbound_connection
    bearer_token = "Bearer %s" % (northbound_access_token)
    northbound_connection.connect(
        northbound_url, headers={"Authorization": bearer_token}
    )


# function to disconnect from the northbound platform upon exit
def disconnect_from_northbound():
    global northbound_connection

    # send the stop stream event to the northbound server
    northbound_connection.emit("stop_device_location_stream")

    # disconnect from northbound server
    northbound_connection.disconnect()


# function to configure logging
def configure_logging(app):
    # deactivate default flask logger
    app.logger.removeHandler(default_handler)

    # create file handler object
    file_handler = RotatingFileHandler("colorum.log", maxBytes=16384, backupCount=20)

    # set logging level of file handler
    file_handler.setLevel(logging.INFO)

    # create file formatter object
    file_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s [in %(filename)s: %(lineno)d]"
    )

    # apply file formatter to file handler
    file_handler.setFormatter(file_formatter)

    # add file handler to logger
    app.logger.addHandler(file_handler)


# function to configure blueprints
def register_blueprints(app):
    from app.main import main_blueprint

    app.register_blueprint(main_blueprint)
