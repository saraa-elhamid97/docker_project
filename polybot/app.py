import flask
from flask import request
import os
from bot import ObjectDetectionBot, Bot, QuoteBot

app = flask.Flask(__name__)

telegram_token_path = os.environ['TELEGRAM_TOKEN_FILE']
with open(telegram_token_path, 'r') as secret_file:
    TELEGRAM_TOKEN = secret_file.read()


TELEGRAM_APP_URL = os.environ['TELEGRAM_APP_URL']


@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


if __name__ == "__main__":
    bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL)

    app.run(host='0.0.0.0', port=8443)


