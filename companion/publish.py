import os
from multiprocessing import Queue

import pika

from tenacity import (
    retry, 
    stop_after_attempt, stop_after_delay, wait_exponential,
)

from config.logging import logger


RABBIT_IP = os.getenv("RABBIT_IP", "10.100.59.176")
USER = 'user'
PASSWORD = os.getenv("RABBITMQ_PASSWORD", "o1mB8moVLo")
APPLICATION = os.getenv("APPLICATION", "#APPLICATION")


def with_retry_publish(data: str, target_queue: str, deadletter_queue: Queue) -> pika.BlockingConnection:
    try:
        publish_message(data, target_queue)
    except:
        logger.warn('failed to publish message. triggering failover...')
        deadletter_queue.put(data)
        logger.info('message put to failover queue')


def publish_failover(deadletter_queue: Queue, target_queue: str) -> None:
    while True:
        if not deadletter_queue.empty():
            data = deadletter_queue.get()
            try:
                publish_message(data, target_queue)
            except:
                logger.warn('failed to publish DLQ message. triggering failover...')
                deadletter_queue.put(data)
                logger.info('message put to failover queue')


@retry(
        wait=wait_exponential(multiplier=1, min=0, max=10),
        stop=(stop_after_attempt(5) | stop_after_delay(15)),
)
def publish_message(data: str, target_queue: str):
    data_bytes = data.encode('utf-8')
    credentials = pika.PlainCredentials(USER, PASSWORD)
    publish_connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBIT_IP,
            credentials=credentials,
            virtual_host=APPLICATION
        )
    )
    
    channel = publish_connection.channel()
    status = channel.queue_declare(
        queue=target_queue, 
        durable=True,
    )
    
    if status.method.message_count == 0:
        logger.info("queue empty")

    channel.basic_publish(
        exchange='',
        routing_key=target_queue,
        body=data_bytes,
        properties=pika.BasicProperties(
            delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
        )
    )
    logger.info("message delivered")
    
    publish_connection.close()
    