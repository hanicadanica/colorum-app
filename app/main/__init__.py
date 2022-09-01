from flask import Blueprint

main_blueprint = Blueprint("main", __name__)

# from . import route, northbound_handler
from . import routes, northbound_handler, admin_routes, event_handler
