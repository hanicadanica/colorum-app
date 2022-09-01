#!/usr/bin/env python
from pyproj import CRS, Transformer
from dotenv import load_dotenv
from datetime import timedelta
import os

# load from .env file
load_dotenv()


class Config:
    # default setting
    FLASK_ENV = "development"
    DEBUG = False
    TESTING = False

    # database
    database_url = os.getenv("DATABASE_URL")
    database_username = os.getenv("DATABASE_USERNAME")
    database_password = os.getenv("DATABASE_PASSWORD")
    database_name = os.getenv("DATABASE_NAME")

    if database_url:
        SQLALCHEMY_DATABASE_URI = "postgresql://%s:%s@%s:5432/%s" % (
            database_username,
            database_password,
            database_url,
            database_name,
        )
    else:
        SQLALCHEMY_DATABASE_URI = (
            "postgresql://postgres:postgres@localhost:5432/colorum_app"
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "max_overflow": 1000,
        "pool_size": 1000,
        "pool_recycle": 300,
    }

    # cors
    CORS_HEADERS = "Content-Type"

    # for colorum app
    COLORUM_MAX_DISTANCE = os.getenv("COLORUM_MAX_DISTANCE", default=100)
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", default="gpx_files")
    ALLOWED_EXTENSIONS = ["gpx"]

    # for access tokens
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", default="")
    access_token_expiry = os.getenv("JWT_ACCESS_TOKEN_EXPIRES")
    if access_token_expiry:
        JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(access_token_expiry))
    else:
        JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    refresh_token_expiry = os.getenv("JWT_REFRESH_TOKEN_EXPIRES")
    if refresh_token_expiry:
        JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(refresh_token_expiry))
    else:
        JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers"]

    # northbound credentials
    NORTHBOUND_USERNAME = os.getenv("NORTHBOUND_USERNAME", default="")
    NORTHBOUND_PASSWORD = os.getenv("NORTHBOUND_PASSWORD", default="")
    NORTHBOUND_ADDRESS = os.getenv("NORTHBOUND_ADDRESS", default="127.0.0.1")
    NORTHBOUND_PORT = os.getenv("NORTHBOUND_PORT", default=23456)

    # secret key
    SECRET_KEY = os.getenv("SECRET_KEY")

    # projection for projecting GPS coordinates onto a map projection suitable for the Philipines
    WGS84 = CRS("EPSG:4326")
    PSEUDO_MERCATOR = CRS("EPSG:32651")
    PROJECTION = Transformer.from_crs(WGS84, PSEUDO_MERCATOR).transform


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    FLASK_ENV = "production"
