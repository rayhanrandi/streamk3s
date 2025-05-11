import os
from multiprocessing import Queue

import pika

from tenacity import (
    retry, 
    stop_after_attempt, stop_after_delay, wait_exponential,
    RetryError
)

from config.global_logger import logger


RABBIT_IP = os.getenv("RABBIT_IP", "10.100.59.176")
USER = 'user'
PASSWORD = os.getenv("RABBITMQ_PASSWORD", "o1mB8moVLo")
APPLICATION = os.getenv("APPLICATION", "#APPLICATION")


def with_retry_publish(data: str, target_queue: str, deadletter_queue: Queue, source: str = 'child-proc') -> None:
    """
    Wrapper function to attach failover behavior to the message publishing process.
    This function will call the `publish_message` function that has a retry mechanism attached,
    and put messages into a shared DLQ if the publishing process fails to publish the message within the retry constraints.
    """
    try:
        _publish_message(data, target_queue)
    except RetryError as e:
        logger.warn(f'[{source} publisher PID {os.getpid()}] - failed to publish message: {str(e)}. triggering failover...')
        _failover(data, deadletter_queue)
    else:
        logger.info(f'[{source} publisher PID {os.getpid()}] - success with process stat: {_publish_message.retry.statistics}')


def publish_failover(deadletter_queue: Queue, target_queue: str) -> None:
    """
    Failover mechanism to re-publish failed messages from an in-memory DLQ that is shared between processes.
    The mechanism runs indefinitely in the background as a child process to the interface,
    which will publish messages in batches of 100.
    """
    while True:
        if (not deadletter_queue.empty()) and (deadletter_queue.qsize() >= 100):
            data = deadletter_queue.get()
            with_retry_publish(data, target_queue, deadletter_queue, source='DLQ')


@retry(
        wait=wait_exponential(multiplier=2, min=0, max=10),
        stop=(stop_after_attempt(3) | stop_after_delay(10)),
)
def _publish_message(data: str, target_queue: str):
    """
    Main publishing process. The process will try to declare the target queue if it has not yet been declared, and will
    create both `BlockingConnection` and `BlockingChannel` for each message which will be used to publish the message.
    
    In the event where the message fails to be published, this process will retry the publishing process within the constraints
    of max retry count, total delay, and exponential backoff defined in the `@retry` decorator.
    """
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
        logger.info(f"[publisher PID {os.getpid()}] - queue empty")

    channel.basic_publish(
        exchange='',
        routing_key=target_queue,
        body=data_bytes,
        properties=pika.BasicProperties(
            delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
        )
    )
    
    publish_connection.close()


def _failover(data: str, deadletter_queue: Queue) -> None:
    deadletter_queue.put(data)
