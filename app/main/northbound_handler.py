from . import main_blueprint, calculation_functions
from app.models import GPSDevice, Route
from app import db

from flask import request, current_app
from datetime import datetime
from json import loads, dumps

import logging
import os


@main_blueprint.route("/list_of_gps_devices", methods=["POST"])
def handle_gps_data_from_northbound():
    data = request.get_json()

    for gps_device in data:
        # for each GPS device coming from the data stream, determine whether it is within the route it is associated with
        # and also get the distance from the GPS device to its associated route

        associated_route = gps_device["associated_route"]
        gps_device_id = gps_device["gps_device_id"]
        last_location = gps_device["last_location"]

        # check if GPS device already exists in the db
        current_gps_device = GPSDevice.query.filter_by(id=gps_device_id).first()
        if current_gps_device is None:
            # if GPS device does not exist, add it to the database
            current_gps_device = GPSDevice(
                gps_device_id, last_location, associated_route
            )
            db.session.add(current_gps_device)
            db.session.commit()
        else:
            # if GPS device already exists, update its last location and associated route
            current_gps_device.online = True
            current_gps_device.associated_route = associated_route
            current_gps_device.last_location = last_location

            db.session.commit()

        # check if the route associated with the gps device
        # has a corresponding .gpx file
        db_route = Route.query.filter_by(id=associated_route).first()
        if db_route is not None and db_route.gpx_filename is not None:
            try:
                # open the .gpx file and convert it to a route list using convert_gpx_file_to_list
                gpx_file = open(
                    os.path.join(
                        current_app.config["UPLOAD_FOLDER"], db_route.gpx_filename
                    ),
                    "r",
                )
                route_points = calculation_functions.convert_gpx_file_to_list(gpx_file)
                gpx_file.close()

                # use the point_is_within_route function to check if the gps device
                # is within its associated route
                (
                    within_route,
                    device_to_route_distance,
                ) = calculation_functions.point_is_within_route(
                    current_gps_device.last_location, route_points
                )

                # update the gps device to route distance
                current_gps_device.distance_to_route = device_to_route_distance

                if not within_route:
                    # if a gps device is not within its associated route
                    # (i.e. it is farther from the route than the set maximum distance),
                    # set is_colorum of the gps device to true
                    current_gps_device.is_colorum = True
                else:
                    # if a gps device is within its associated route
                    # set is_colorum of the gps device to false
                    current_gps_device.is_colorum = False

                db.session.commit()
            except Exception as error:
                logging.error(str(error))

    return "OK"


# event handler for when the northbound platform sends over route data
@main_blueprint.route("/list_of_routes", methods=["POST"])
def handle_get_routes_from_northbound():
    data = request.get_json()

    received_routes = [route["route_id"] for route in data]
    for route_id in received_routes:
        db_route = Route.query.filter_by(id=route_id).first()
        if db_route is None:
            new_route = Route(route_id)
            db.session.add(new_route)
            db.session.commit()

    all_routes = Route.query.all()
    routes_to_delete = []
    for route in all_routes:
        if route.id not in received_routes:
            routes_to_delete.append(route)

    for route in routes_to_delete:
        db.session.delete(route)
        db.session.flush()

    db.session.commit()

    return "OK"
