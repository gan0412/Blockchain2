from waitress import serve
from App import app
from Config import HOST, PORT

if __name__ == '__main__':
    serve(app, host=HOST, port=PORT)