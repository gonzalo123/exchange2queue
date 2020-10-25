from flask import Flask, request
from flask import jsonify

import settings
from lib.auth import authorize_bearer
from lib.logger import logger
from lib.rabbit import get_channel
import json

app = Flask(__name__)


@app.route('/health')
def health():
    return jsonify({"status": "ok"})


@app.route('/publish/<path:exchange>', methods=['POST'])
@authorize_bearer(bearer=settings.API_TOKEN)
def publish(exchange):
    channel = get_channel()
    try:
        message = request.get_json()
        channel.basic_publish(
            exchange=exchange,
            routing_key='',
            body=json.dumps(message)
        )
        logger.info(f"message sent to exchange {exchange}")
        return jsonify({"status": "OK", "exchange": exchange})
    except:
        return jsonify({"status": "NOK", "exchange": exchange})
