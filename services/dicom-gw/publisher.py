# services/dicom-gw/publisher.py
import pika
import json
import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
QUEUE_NAME = "new_study"

def publish_study_summary(study_uid, patient_name, modality, num_slices):
    message = {
        "StudyInstanceUID": study_uid,
        "PatientName": patient_name,
        "Modality": modality,
        "NumberOfSlices": num_slices
    }

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )
    channel = connection.channel()

    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2  # Make message persistent
        )
    )
    print(f"[x] Published study {study_uid} with {num_slices} slices to queue.")

    connection.close()
