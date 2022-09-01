from app import (
    db,
    northbound_connection,
    northbound_access_token,
    northbound_refresh_token,
)
from app.models import ColorumAdmin, ColorumUser, Route
from . import main_blueprint

from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
    create_access_token,
    create_refresh_token,
)
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
from requests.auth import HTTPBasicAuth
from passlib.hash import pbkdf2_sha256
from shortuuid import ShortUUID
from base64 import b64decode
from ast import literal_eval
from socketio import Client
from requests import post
from time import sleep

import os

# create local socketio connection to northbound interface
local_northbound_connection = Client()


@local_northbound_connection.on("list_of_routes")
def handle_get_routes_from_northbound_local(data):
    post("http://127.0.0.1:34568/list_of_routes", json=data)


# function to check if file has valid file extension
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_EXTENSIONS"]
    )


# login using admin username and password to get access tokens to be used in other routes
@main_blueprint.route("/login/", methods=["POST"])
def handle_login():
    # check if admin username and password were supplied in the header
    if "Authorization" not in request.headers:
        current_app.logger.error(
            "Admin trying to log in has not provided username/password"
        )
        return "username and password were not supplied", 401

    # get admin username and password from header
    username_password = (
        b64decode(request.headers["Authorization"].split()[-1])
        .decode("utf-8")
        .split(":")
    )
    admin_username = username_password[0]
    admin_password = username_password[1]

    # get admin information from the db
    admin = ColorumAdmin.query.filter_by(id=admin_username).first()
    if admin:
        # if admin exists in the db, verify the password used for logging in against the hash in the db
        if not pbkdf2_sha256.verify(admin_password, admin.password):
            # if the password and the hash don't match, return error
            current_app.logger.error(
                "Admin account %s username and password do not match", admin_username
            )
            return "username and password do not match", 401
    else:
        # if admin does not exist in the db, return error
        current_app.logger.error(
            "Admin account %s trying to log in does not exist", admin_username
        )
        return "username does not exist", 404

    try:
        # create access and refresh tokens for admin logging in
        access_token = create_access_token(identity=admin_username)
        refresh_token = create_refresh_token(identity=admin_username)

        # return tokens
        current_app.logger.info(
            "Admin %s has logged in. Access token: %s. Refresh token: %s.",
            admin_username,
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


# set the username and password to be used for the connection with the Northbound Interface
@main_blueprint.route("/set_northbound_credentials/", methods=["PUT"])
@jwt_required()
def handle_set_username_password():
    try:
        # get json from request
        json = request.get_json()
    except:
        # no json found in request
        current_app.logger.error("no json found in request")
        return "no JSON found in request", 400

    try:
        # get username and password
        username_password = (
            b64decode(json["northbound_credentials"]).decode("utf-8").split(":")
        )
        username = username_password[0]
        password = username_password[1]

        # send login request to northbound platform
        northbound_url = "http://%s:%s" % (
            current_app.config["NORTHBOUND_ADDRESS"],
            current_app.config["NORTHBOUND_PORT"],
        )
        northbound_login_url = "%s/login/" % (northbound_url,)
        northbound_login = post(
            northbound_login_url, auth=HTTPBasicAuth(username, password)
        )

        if northbound_login.status_code != 200:
            current_app.logger.error(northbound_login.text)
            return northbound_login.text, northbound_login.status_code

        # get access and refresh tokens from request response
        global northbound_access_token, northbound_refresh_token
        northbound_response_json = northbound_login.json()
        northbound_access_token = northbound_response_json["access_token"]
        northbound_refresh_token = northbound_response_json["refresh_token"]

        # disconnect from the Northbound Interface
        northbound_connection.disconnect()

        sleep(1)

        # connect to the northbound platform using socketio connect
        bearer_token = "Bearer %s" % (northbound_access_token)
        northbound_connection.connect(
            northbound_url, headers={"Authorization": bearer_token}
        )

        # send the start stream event to the northbound server
        northbound_connection.emit("start_device_location_stream")

        current_app.logger.info("Successfully updated Northbound Interface credentials")
        return "successfully updated Northbound Interface credentials", 200
    except Exception as error:
        current_app.logger.error(str(error))
        return str(error), 500


# route for creating a colorum app user account
# account username must be provided
@main_blueprint.route("/create_colorum_user/", methods=["POST"])
@jwt_required()
def handle_create_colorum_user():
    try:
        # get json from request
        json = request.get_json()
    except:
        # no json found in request
        current_app.logger.error("no json found in request")
        return "no JSON found in request", 400

    if "colorum_username" not in json:
        # incomplete data sent
        current_app.logger.error("missing colorum user username")
        return "colorum user username is missing", 400

    try:
        # get client username from json
        colorum_username = json["colorum_username"]

        # generate password for client and get the hash of it
        colorum_password = ShortUUID().random(length=10)
        password_hash = pbkdf2_sha256.hash(colorum_password)

        # check if client username already exists
        colorum_user_exists = ColorumUser.query.filter_by(id=colorum_username).first()
        if colorum_user_exists:
            current_app.logger.error("Colorum user %s already exists", colorum_username)
            return "colorum user already exists", 400
        else:
            # add colorum user to database
            new_colorum_user = ColorumUser(colorum_username, colorum_password)
            db.session.add(new_colorum_user)
            db.session.commit()

            current_app.logger.info(
                "Colorum user %s successfully created", colorum_username
            )
            return jsonify({"password": colorum_password}), 200
    except Exception as error:
        current_app.logger.error(str(error))
        return str(error), 500


# route for getting all colorum app user accounts
@main_blueprint.route("/get_colorum_users/", methods=["GET"])
@jwt_required()
def handle_get_colorum_users():
    try:
        # list of colorum app users
        colorum_users = []

        # get colorum app users
        all_colorum_users = ColorumUser.query.all()
        for colorum_user in all_colorum_users:
            colorum_users.append(colorum_user.id)

        current_app.logger.info("Colorum users: %s", colorum_users)
        return jsonify(colorum_users), 200
    except Exception as error:
        current_app.logger.error(str(error))
        return str(error), 500


# route for deleting a colorum app user account
@main_blueprint.route("/delete_colorum_user/<colorum_user_id>", methods=["DELETE"])
@jwt_required()
def handle_delete_colorum_user(colorum_user_id):
    if not colorum_user_id:
        # if colorum app user id was not specified, return error 400
        current_app.logger.error("No colorum user id specified")
        return "no colorum user id specified", 400

    try:
        # get colorum app user
        colorum_user = ColorumUser.query.filter_by(id=colorum_user_id).first()

        # check if colorum user exists
        if not colorum_user:
            current_app.logger.error("Colorum user %s does not exist", colorum_user_id)
            return "colorum user does not exist", 404

        # delete colorum user from database
        db.session.delete(colorum_user)
        db.session.flush()
        db.session.commit()

        current_app.logger.info("Colorum user %s successfully deleted", colorum_user_id)
        return "colorum user successfully deleted", 200
    except Exception as error:
        current_app.logger.error(str(error))
        return str(error), 500


# get the routes from the Northbound Interface that the ETA app can access
@main_blueprint.route("/get_routes/", methods=["GET"])
@jwt_required()
def handle_get_routes():
    try:
        # list of dicts of routes to send back along with whether or not they have
        # associated gpx files already
        routes_to_send = []

        if (
            current_app.config["NORTHBOUND_USERNAME"]
            and current_app.config["NORTHBOUND_PASSWORD"]
        ):
            # login to northbound interface using northbound credentials
            northbound_url = "http://%s:%s" % (
                current_app.config["NORTHBOUND_ADDRESS"],
                current_app.config["NORTHBOUND_PORT"],
            )
            northbound_login_url = "%s/login/" % (northbound_url,)
            northbound_login = post(
                northbound_login_url,
                auth=HTTPBasicAuth(
                    current_app.config["NORTHBOUND_USERNAME"],
                    current_app.config["NORTHBOUND_PASSWORD"],
                ),
            )

            if northbound_login.status_code != 200:
                current_app.logger.error(northbound_login.text)
                return northbound_login.text, northbound_login.status_code

            # get access token from request response
            northbound_response_json = northbound_login.json()
            northbound_access_token = northbound_response_json["access_token"]

            # connect to the northbound interface
            global local_northbound_connection
            bearer_token = "Bearer %s" % (northbound_access_token)
            local_northbound_connection.connect(
                northbound_url, headers={"Authorization": bearer_token}
            )

            # send the socketio event that gets the routes
            # northbound_connection.emit('get_routes')
            local_northbound_connection.emit("get_routes")

            sleep(0.5)

            local_northbound_connection.disconnect()

        # # send the socketio event that gets the routes
        # northbound_connection.emit("get_routes")

        # sleep(0.5)

        # for each route in available_routes, check if there is a gpx file associated with the route
        all_routes = Route.query.all()
        for route in all_routes:
            # check if the route has a gpx file associated with it
            # if it does, append route to routes_to_send with the gpx file filename
            # if it doesn't, append route to routes_to_send without any gpx file filename
            if route.gpx_filename is not None:
                gpx_filename = secure_filename(route.gpx_filename)
                gpx_file_path = os.path.join(
                    current_app.config["UPLOAD_FOLDER"], gpx_filename
                )

                if os.path.exists(gpx_file_path):
                    routes_to_send.append(
                        {
                            "route_id": route.id,
                            "gpx_file_associated": route.gpx_filename,
                        }
                    )
                else:
                    routes_to_send.append(
                        {"route_id": route.id, "gpx_file_associated": None}
                    )
            else:
                routes_to_send.append(
                    {"route_id": route.id, "gpx_file_associated": None}
                )

        # return the routes
        current_app.logger.info("Available routes: %s", routes_to_send)
        return jsonify(routes_to_send), 200
    except Exception as error:
        current_app.logger.error(str(error))
        return str(error), 500


# associate a GPX file to a route
@main_blueprint.route("/associate_file_to_route/", methods=["POST"])
@jwt_required()
def handle_associate_file_to_route():
    # list of errors found
    list_of_errors = []

    # get route ID
    get_route_id = literal_eval(request.form["body"])
    if "route_id" not in get_route_id:
        # if the route ID was not specified, add to list of errors
        list_of_errors.append("no route ID specified")
    else:
        route_id = get_route_id["route_id"]

    # get GPX file
    if "file" not in request.files:
        # if no file was found in the request, add to list of errors
        list_of_errors.append("no GPX file found in the request")
    else:
        # file to read coordinates from
        gpx_file = request.files["file"]

        if gpx_file.filename == "":
            # if no file was selected, add to list of errors
            list_of_errors.append("no GPX file was selected")
        elif gpx_file.filename != "" and not allowed_file(gpx_file.filename):
            # if file is of the wrong extension, add to list of errors
            list_of_errors.append("file has wrong extension")

    if list_of_errors:
        # if there is at least one error, return the list of errors
        # and do not proceed to associating GPX file with route
        current_app.logger.error(list_of_errors)
        return jsonify(list_of_errors), 400

    try:
        # save GPX file to the upload folder with the route ID as the filename
        # gpx_filename = secure_filename(route_id + '.gpx')
        gpx_filename = secure_filename(gpx_file.filename)
        gpx_file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], gpx_filename)
        gpx_file.save(gpx_file_path)

        # check if route already has an entry in the db
        db_route = Route.query.filter_by(id=route_id).first()
        if db_route:
            # if route exists in the db, update the association with the newly added gpx file
            db_route.gpx_filename = gpx_filename
        else:
            # if route does not exist in the db, add to db with the gpx file association
            new_route = Route(route_id, gpx_filename)
            db.session.add(new_route)
        db.session.commit()

        current_app.logger.info("Associated GPX file to route %s", route_id)
        return "successfully associated GPX file with route", 200
    except Exception as error:
        current_app.logger.error(str(error))
        return str(error), 500


# delete all of the GPX files (that represent routes) from the GPX file upload folder
@main_blueprint.route("/nuke/", methods=["DELETE"])
@jwt_required()
def handle_nuke():
    try:
        for gpx_filename in os.listdir(current_app.config["UPLOAD_FOLDER"]):
            # delete each file from GPX file upload folder
            gpx_file_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], gpx_filename
            )
            os.remove(gpx_file_path)

        Route.query.delete()
        db.session.commit()

        current_app.logger.info("Successfully deleted all GPX files")
        return "successfully deleted all GPX files", 200
    except Exception as error:
        current_app.logger.error(str(error))
        return str(error), 500


# refresh access token if it is expired
# refresh token must be provided
@main_blueprint.route("/refresh/", methods=["POST"])
@jwt_required(refresh=True)
def handle_refresh_token():
    try:
        # get admin identity
        admin_username = get_jwt_identity()

        # create new access and refresh tokens
        access_token = create_access_token(identity=admin_username)
        refresh_token = create_refresh_token(identity=admin_username)

        # return tokens
        current_app.logger.info(
            "Admin %s has been issued new tokens. Access token: %s. Refresh token: %s.",
            admin_username,
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
