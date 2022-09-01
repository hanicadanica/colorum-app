from app import northbound_connection
from requests import post


@northbound_connection.on("list_of_routes")
def handle_list_of_routes(data):
    post("http://127.0.0.1:34568/list_of_routes", json=data)


@northbound_connection.on("list_of_gps_devices")
def handle_gps_data_stream(data):
    post("http://127.0.0.1:34568/list_of_gps_devices", json=data)
