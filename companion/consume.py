import os
import sys
import time
import logging
import json
import pika
import requests
from requests.auth import HTTPBasicAuth

from config.logging import logger


rabbit_ip = os.getenv("RABBIT_IP", "10.100.59.176")
user = 'user'
password = os.getenv("RABBITMQ_PASSWORD", "o1mB8moVLo")
application = os.getenv("APPLICATION", "#application")


def callback(ch, method, properties, body):
    my_json = body.decode('utf8')
    json_format = json.dumps(my_json, indent=4, sort_keys=False)
    pod_ip = os.getenv("MY_POD_IP", "0.0.0.0")
    operator_port = os.getenv("OPERATOR_PORT", "4322")
    operator_path = os.getenv("OPERATOR_PATH", "/post_message")
    ip = 'http://' + pod_ip + ':' + operator_port + operator_path
    post = requests.post(ip, json=json.loads(json_format))
    if post.status_code == 200:
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logging.info(" message consumed ")
    else:
        ch.basic_nack(delivery_tag=method.delivery_tag)
    return json_format


def consume_message(queue):
    credentials = pika.PlainCredentials(user, password)
    consume_connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=rabbit_ip,
                                  credentials=credentials,
                                  virtual_host=application,
                                  ))
    channel = consume_connection.channel()
    channel.basic_qos(prefetch_count=10)
    result = channel.basic_consume(queue=queue,
                                   auto_ack=False,
                                   on_message_callback=callback)
    logger.info(' [*] Waiting for messages.')
    channel.start_consuming()
    channel.stop_consuming()
    return result
