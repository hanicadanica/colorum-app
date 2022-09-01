from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY
from json import dumps


class GPSDevice(db.Model):
    __tablename__ = "gps_devices"

    id = db.Column(db.String(), primary_key=True, unique=True)
    online = db.Column(db.Boolean(), nullable=False)
    last_location = db.Column(ARRAY(db.Float()))
    associated_route = db.Column(db.String())
    distance_to_route = db.Column(db.Float())
    is_colorum = db.Column(db.Boolean(), nullable=False)

    def __init__(self, id, last_location, associated_route):
        self.id = id
        self.online = True
        self.last_location = last_location
        self.associated_route = associated_route
        self.distance_to_route = 0
        self.is_colorum = False

    def __repr__(self):
        return "<GPS device %r>" % self.id


class Route(db.Model):
    __tablename__ = "puv_routes"

    id = db.Column(db.String(), primary_key=True, unique=True)
    gpx_filename = db.Column(db.String())

    def __init__(self, id, gpx_filename=None):
        self.id = id
        self.gpx_filename = gpx_filename

    def __repr__(self):
        return "<GPX Route Association %r: %r>" % (self.id, self.gpx_file)


class ColorumAdmin(db.Model):
    __tablename__ = "colorum_admins"

    id = db.Column(db.String(), primary_key=True, unique=True)
    password = db.Column(db.String, nullable=False)

    def __repr__(self):
        return "<ETA Admin %r>" % self.id


class ColorumUser(db.Model):
    __tablename__ = "colorum_users"

    id = db.Column(db.String(), primary_key=True, unique=True)
    password = db.Column(db.String, nullable=False)

    def __init__(self, id, password):
        self.id = id
        self.password = password

    def __repr__(self):
        return "<ETA Admin %r>" % self.id
