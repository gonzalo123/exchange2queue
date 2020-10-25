## Playing with RabbitMQ and Python. Exchanges and queues

Lately in all my projects message queues appear in one way or another. Normally I work with AWS and I use SQS and SNS, but I also use quite often, RabbitMQ and MQTT. In AWS there's something that I use a lot to isolate services. The process that emits messages emits message to SNS and I bind SNS to SQS. With this technique I can attach n SQS to the the same SNS. I've used it [here](https://github.com/gonzalo123/django_reactive_users). In AWS is pretty straightforward to do that. Today We're going to do the same with RabbitMQ. In fact it's very easy to do it in RabbitMQ. We only need to follow the tutorial in official RabbitMQ [documentation](https://www.rabbitmq.com/getstarted.html).

The script listen to a exchange and resend the message to a queue topic. Basically the same that we can see within RabbitMQ's documentation.

```python
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
```

We send one message to the exchange using rabbitmqadmin and see the message in the queue:

```
rabbitmqadmin -u username -p password publish exchange=exchange routing_key= payload="hello, world"
```

My idea with this project is to deploy it into a docker swarm cluster and add/remove listener only adding new services to the stack:

```yaml
  ...
  exchange2topic1:
    image: ${ECR}/exchange2queue:${VERSION}
      build:
        context: .
        dockerfile: Dockerfile
      deploy:
        restart_policy:
          condition: on-failure
      depends_on:
        - rabbit
    command: /bin/sh wait-for-it.sh rabbit:5672 -- python exchange2queue.py
    environment:
      RABBIT_HOST: rabbit
      RABBIT_USER: ${RABBITMQ_USER}
      RABBIT_PASS: ${RABBITMQ_PASS}
      EXCHANGE: exchange
      QUEUE_TOPIC: topic1
      QUEUE_DURABLE: 1
      QUEUE_AUTO_DELETE: 0
  ...
```

With this approach it's very simple form me add and remove new listeners without touching the emitter

Also, as plus, I like to add a simple http api to allow me to send messages to the exchange with a post request, instead of using a RabbitMQ client. That's because sometimes I work with legacy systems where using a AMQP client isn't simple. That's a simple Flask API

```python
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
```

Now we can emit messages to the exchange using curl, postman or any other http client.

```http request
POST http://localhost:5000/publish/exchange
Content-Type: application/json
Authorization: Bearer super_secret_key

{
  "hello": "Gonzalo"
}
```

Also, in the docker stack I want to use a reverse proxy to server my Flask application (served with gunicorn) and the RabbitMQ management console. I'm using nginx to do that:

```
upstream api {
    server api:5000;
}

server {
    listen 8000 default_server;
    listen [::]:8000;

    client_max_body_size 20M;

    location / {
        try_files $uri @proxy_to_api;
    }

    location ~* /rabbitmq/api/(.*?)/(.*) {
        proxy_pass http://rabbit:15672/api/$1/%2F/$2?$query_string;
        proxy_buffering                    off;
        proxy_set_header Host              $http_host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ~* /rabbitmq/(.*) {
        rewrite ^/rabbitmq/(.*)$ /$1 break;
        proxy_pass http://rabbit:15672;
        proxy_buffering                    off;
        proxy_set_header Host              $http_host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location @proxy_to_api {
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Url-Scheme $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_redirect off;

        proxy_pass http://api;
    }
}
```

And that's all. Here the docker-compose.yml

```yaml
version: '3.6'

x-base: &base
  image: ${ECR}/exchange2queue:${VERSION}
  build:
    context: .
    dockerfile: Dockerfile
  deploy:
    restart_policy:
      condition: on-failure
  depends_on:
    - rabbit

services:
  rabbit:
    image: rabbitmq:3-management
    deploy:
      restart_policy:
        condition: on-failure
    ports:
      - 5672:5672
    environment:
      RABBITMQ_ERLANG_COOKIE:
      RABBITMQ_DEFAULT_VHOST: /
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASS}

  nginx:
    image: ${ECR}/exchange2queue_nginx:${VERSION}
    deploy:
      restart_policy:
        condition: on-failure
    build:
      context: .docker/nginx
      dockerfile: Dockerfile
    ports:
      - 8080:8000
    depends_on:
      - rabbit
      - api

  api:
    <<: *base
    container_name: front
    command: /bin/sh wait-for-it.sh rabbit:5672 -- gunicorn -w 4 api:app -b 0.0.0.0:5000
    deploy:
      restart_policy:
        condition: on-failure
    environment:
      RABBIT_HOST: rabbit
      RABBIT_USER: ${RABBITMQ_USER}
      RABBIT_PASS: ${RABBITMQ_PASS}
      API_TOKEN: ${API_TOKEN}

  exchange2topic1:
    <<: *base
    command: /bin/sh wait-for-it.sh rabbit:5672 -- python exchange2queue.py
    environment:
      RABBIT_HOST: rabbit
      RABBIT_USER: ${RABBITMQ_USER}
      RABBIT_PASS: ${RABBITMQ_PASS}
      EXCHANGE: exchange
      QUEUE_TOPIC: topic1
      QUEUE_DURABLE: 1
      QUEUE_AUTO_DELETE: 0

  exchange2topic2:
    <<: *base
    command: /bin/sh wait-for-it.sh rabbit:5672 -- python exchange2queue.py
    environment:
      RABBIT_HOST: rabbit
      RABBIT_USER: ${RABBITMQ_USER}
      RABBIT_PASS: ${RABBITMQ_PASS}
      EXCHANGE: exchange
      QUEUE_TOPIC: topic2
      QUEUE_DURABLE: 1
      QUEUE_AUTO_DELETE: 0
```

