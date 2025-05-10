import json
import os

from multiprocessing import Process, Queue

import consume
import publish

import flask
import pika

from flask import Flask, jsonify

from config.logging import logger


QUEUE_MAXSIZE: int = 10000

app = Flask(__name__)

deadletter_queue: Queue = Queue(maxsize=QUEUE_MAXSIZE)

queue = os.getenv("OUTPUT_QUEUE", "#queue")
termination = os.getenv("TERMINATION_QUEUE", "#termination")


# class MessageQueue:

#     _APPLICATION = os.getenv("APPLICATION", "#APPLICATION")
#     _RABBIT_IP = os.getenv("RABBIT_IP", "10.100.59.176")
#     _USER = 'user'
#     _PASSWORD = os.getenv("RABBITMQ_PASSWORD", "o1mB8moVLo")

#     def __init__(self) -> None:
#         """
#         Initializes a BlockingConnection to RabbitMQ.
#         """
#         logger.info('initializing BlockingConnection and BlockingChannel...')
#         try:
#             self._credentials = pika.PlainCredentials(self._USER, self._PASSWORD)
#             self._conn_params = pika.ConnectionParameters(
#                 host=self._RABBIT_IP,
#                 credentials=self._credentials,
#                 virtual_host=self._APPLICATION
#             )
#             self._conn = pika.BlockingConnection(self._conn_params)
#             self._is_connected = Value('i', 1)
#         except Exception as e:
#             logger.error(f'error while initializing connection: {str(e)}')

#     @retry(wait=wait_exponential(multiplier=1, min=0, max=3))
#     def reconnect(self) -> None:
#         try:
#             self._conn.close()
#         except:
#             pass
#         self._conn = pika.BlockingConnection(self._conn_params)

#     def get_connection(self) -> pika.BlockingConnection:
#         return self._conn
    

@app.route("/post_message", methods=["POST"])
async def post():
    json_string = flask.request.data.decode("utf-8")

    try:
        json_data = json.loads(json_string)
    except json.JSONDecodeError as e:
        logger.error(f"Failed while decoding JSON data: {e.msg}")
        return jsonify({"error": "Invalid JSON data"}), 400

    target_queue = queue
    if json_data.get("status") and termination != "#termination":
        logger.info("Termination message received.")
        target_queue = termination

    # publish message in child processes
    logger.info(f'spawning child process to publish message: f{json_string}...')
    p_publisher = Process(
        target=publish.with_retry_publish,
        args=(json_string, target_queue, deadletter_queue,)
    )
    p_publisher.start()

    logger.info(f'DLQ size: {deadletter_queue.qsize()}')
    
    return jsonify(json_data)


@app.route("/get_message", methods=["GET"])
async def get():
    rabbit_input_queue = os.getenv("INPUT_QUEUE", "queue-1")
    json_data = consume.consume_message(rabbit_input_queue)
    return json_data


if __name__ == '__main__':
    p_dlq = Process(
        target=publish.publish_failover,
        args=(deadletter_queue, queue,)
    )
    p_dlq.start()
    app.run(host="0.0.0.0", port=4321)
