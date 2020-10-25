import settings
from lib.logger import logger
from lib.rabbit import get_channel

channel = get_channel()
channel.exchange_declare(
    exchange=settings.EXCHANGE,
    exchange_type='fanout')

result = channel.queue_declare(
    queue='',
    exclusive=True)

queue_name = result.method.queue

channel.queue_bind(
    exchange=settings.EXCHANGE,
    queue=queue_name)

logger.info(f' [*] Waiting for {settings.EXCHANGE}. To exit press CTRL+C')

channel.queue_declare(
    durable=settings.QUEUE_DURABLE,
    auto_delete=settings.QUEUE_AUTO_DELETE,
    queue=settings.QUEUE_TOPIC
)


def callback(ch, method, properties, body):
    channel.basic_publish(
        exchange='',
        routing_key=settings.QUEUE_TOPIC,
        body=body)
    logger.info(f'Message sent to topic {settings.QUEUE_TOPIC}. Message: {body}')


channel.basic_consume(
    queue=queue_name,
    on_message_callback=callback,
    auto_ack=True)

channel.start_consuming()
