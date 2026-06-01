import json
import logging
import os
import sys

import pika
from flask import Flask, request, jsonify
from prometheus_flask_exporter import PrometheusMetrics

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.propagate import set_global_textmap, inject
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:14317"),
        )
    )
)
trace.set_tracer_provider(provider)
set_global_textmap(TraceContextTextMapPropagator())

app = Flask(__name__)
metrics = PrometheusMetrics(app)
FlaskInstrumentor().instrument_app(app)

LOG_DIR = os.getenv("LOG_DIR", "/app/logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler = logging.FileHandler(os.path.join(LOG_DIR, "producer.log"))
file_handler.setFormatter(log_format)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(log_format)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(stdout_handler)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "events")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

tracer = trace.get_tracer(__name__)

def get_rabbitmq_channel():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    )
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    return connection, channel


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json(silent=True)
    if data is None:
        logging.warning("Received request with invalid JSON")
        return jsonify({"error": "Invalid JSON"}), 400

    connection, channel = get_rabbitmq_channel()
    try:
        headers = {}
        inject(headers)

        channel.basic_publish(
            exchange="",
            routing_key=RABBITMQ_QUEUE,
            body=json.dumps(data),
            properties=pika.BasicProperties(
                delivery_mode=2,
                headers=headers,
            ),
        )
        span = trace.get_current_span()
        trace_id = span.get_span_context().trace_id
        logging.info("Published event [trace_id=%s]: %s", format(trace_id, "032x"), json.dumps(data))
        return jsonify({"status": "published"}), 201
    except Exception as e:
        logging.error("Failed to publish event: %s", str(e))
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=25001, debug=True, use_reloader=False)
