import os

RABBIT_HOST = os.getenv('RABBIT_HOST', 'localhost')
RABBIT_PORT = os.getenv('RABBIT_PORT', 5672)
RABBIT_USER = os.getenv('RABBIT_USER', 'username')
RABBIT_PASS = os.getenv('RABBIT_PASS', 'password')

EXCHANGE = os.getenv('EXCHANGE', 'default')
QUEUE_TOPIC = os.getenv('QUEUE_TOPIC', 'default_topic')
QUEUE_DURABLE = bool(os.getenv('QUEUE_DURABLE', 1))
QUEUE_AUTO_DELETE = bool(os.getenv('QUEUE_AUTO_DELETE', 0))

API_TOKEN = os.getenv('API_TOKEN', 'super_secret_token')
