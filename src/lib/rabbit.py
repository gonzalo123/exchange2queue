import pika
import settings


def get_channel():
    credentials = pika.PlainCredentials(
        username=settings.RABBIT_USER,
        password=settings.RABBIT_PASS)

    parameters = pika.ConnectionParameters(
        host=settings.RABBIT_HOST,
        credentials=credentials
    )

    connection = pika.BlockingConnection(
        parameters=parameters
    )

    return connection.channel()
