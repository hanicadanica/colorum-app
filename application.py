from app import create_server

application = create_server()

if __name__ == "__main__":
    application.run(port=34568)
