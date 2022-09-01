from app.models import ColorumUser, GPSDevice
from . import main_blueprint

from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
    create_access_token,
    create_refresh_token,
)
from flask import request, jsonify, current_app
from passlib.hash import pbkdf2_sha256
from base64 import b64decode
from geopy import distance

# login using username and password to get access tokens to be used in other routes
# login is required because only enforcers with accounts may use the colorum app
@main_blueprint.route("/app_login/", methods=["POST"])
def handle_app_login():
    # check if username and password were supplied in the header
    if "Authorization" not in request.headers:
        current_app.logger.error(
            "User trying to log in has not provided username/password"
        )
        return "username and password were not supplied", 401

    # get username and password from header
    username_password = (
        b64decode(request.headers["Authorization"].split()[-1])
        .decode("utf-8")
        .split(":")
    )
    username = username_password[0]
    password = username_password[1]

    # get user information from the db
    colorum_user = ColorumUser.query.filter_by(id=username).first()
    if colorum_user:
        # if user exists in the db, verify the password used for logging in against the hash in the db
        if not pbkdf2_sha256.verify(password, colorum_user.password):
            # if the password and the hash don't match, return error
            current_app.logger.error(
                "User account %s username and password do not match", username
            )
            return "username and password do not match", 401
    else:
        # if user does not exist in the db, return error
        current_app.logger.error(
            "User account %s trying to log in does not exist", username
        )
        return "username does not exist", 404

    try:
        # create access and refresh tokens for user logging in
        access_token = create_access_token(identity=username)
        refresh_token = create_refresh_token(identity=username)

        # return tokens
        current_app.logger.info(
            "User %s has logged in. Access token: %s. Refresh token: %s.",
            username,
            access_token,
            refresh_token,
        )
        return (
            jsonify({"access_token": access_token, "refresh_token": refresh_token}),
            200,
        )
    except Exception as error:
        current_app.logger.error(str(error))
        return str(error), 500


# refresh access token if it is expired
# refresh token must be provided
@main_blueprint.route("/token_refresh/", methods=["POST"])
@jwt_required(refresh=True)
def handle_app_refresh_token():
    try:
        # get user identity
        username = get_jwt_identity()

        # create new access and refresh tokens
        access_token = create_access_token(identity=username)
        refresh_token = create_refresh_token(identity=username)

        # return tokens
        current_app.logger.info(
            "User %s has been issued new tokens. Access token: %s. Refresh token: %s.",
            username,
            access_token,
            refresh_token,
        )
        return (
            jsonify({"access_token": access_token, "refresh_token": refresh_token}),
            200,
        )
    except Exception as error:
        current_app.logger.error(str(error))
        return str(error), 500


# given a GPS point (the location of the app user) and tha maximum search distance from the GPS point,
# get the colorum vehicles within the search area (formed by the GPS point and maximum distance)
# then return all colorum vehicles (those that are far from their associated routes)
@main_blueprint.route("/get_colorum_vehicles/", methods=["GET"])
@jwt_required()
def handle_get_colorum_vehicles():
    # list of dicts  of colorum vehicles
    # format is {'gps_device_id': <gps device id>, 'last_location': [<latitude>, <longitude>], 'associated_route': <route>, 'distance_from_route': <distance>}
    colorum_vehicles = []

    try:
        # get GPS point and search distance from args
        gps_point = [
            float(request.args.get("latitude")),
            float(request.args.get("longitude")),
        ]
        search_distance = float(request.args.get("search_distance"))
    except:
        # no json found in request
        current_app.logger.error("no args/incomplete args found in request")
        return "no arguments/incomplete arguments found in request", 400

    try:
        # go through each colorum vehicle and check whether or not it is within the search distance of the given GPS point
        # if it is, add the colorum vehicle to the list of colorum vehicles to be sent back to the user
        all_colorum_vehicles = GPSDevice.query.filter_by(is_colorum=True).all()
        for colorum_vehicle in all_colorum_vehicles:
            if (
                distance.distance(gps_point, colorum_vehicle.last_location).km
                <= search_distance
            ):
                colorum_vehicles.append(
                    {
                        "gps_device_id": colorum_vehicle.id,
                        "last_location": colorum_vehicle.last_location,
                        "associated_route": colorum_vehicle.associated_route,
                        "distance_from_route": colorum_vehicle.distance_to_route,
                    }
                )

        # return list of colorum vehicles
        current_app.logger.info(
            "Colorum vehicles for GPS point %s with search distance %s: %s",
            gps_point,
            search_distance,
            colorum_vehicles,
        )
        return jsonify(colorum_vehicles), 200
    except Exception as error:
        current_app.logger.error(str(error))
        return str(error), 500
