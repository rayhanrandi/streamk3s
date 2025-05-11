import json
import os

from multiprocessing import Process, Queue

import consume
import publish

import flask

from flask import Flask, jsonify

from config.global_logger import logger


QUEUE_MAXSIZE: int = 10000

app = Flask(__name__)

deadletter_queue: Queue = Queue(maxsize=QUEUE_MAXSIZE)

queue: str = os.getenv("OUTPUT_QUEUE", "#queue")
termination: str = os.getenv("TERMINATION_QUEUE", "#termination")


@app.route("/post_message", methods=["POST"])
def post():
    json_string = flask.request.data.decode("utf-8")

    try:
        json_data = json.loads(json_string)
    except json.JSONDecodeError as e:
        logger.error(f"[interface PID {os.getpid()}] - Failed while decoding JSON data: {e.msg}")
        return jsonify({"error": "Invalid JSON data"}), 400

    target_queue = queue
    if json_data.get("status") and termination != "#termination":
        logger.info(f"[interface PID {os.getpid()}] - Termination message received.")
        target_queue = termination

    # publish message in child processes
    logger.info(f'[interface PID {os.getpid()}] - spawning child process to publish message: f{json_string}...')
    p_publisher = Process(
        target=publish.with_retry_publish,
        args=(json_string, target_queue, deadletter_queue,)
    )
    p_publisher.start()

    logger.info(f'[interface PID {os.getpid()}] - DLQ size: {deadletter_queue.qsize()}')
    
    return jsonify(json_data)


@app.route("/get_message", methods=["GET"])
def get():
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
