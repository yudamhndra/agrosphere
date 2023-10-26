from typing import Optional, List, Dict
import os
import firebase_admin
from firebase_admin.credentials import Certificate
from firebase_admin.messaging import Message, MulticastMessage, Notification, FCMOptions, AndroidConfig, BatchResponse
from firebase_admin import messaging

certificate: Certificate = Certificate("firebase/agroshere-firebase-adminsdk-gm252-7be1e6d64a.json")
firebase_admin.initialize_app(credential=certificate)
device_token: str = os.getenv("ANDROID_DEVICE_TOKEN1")


def send_topic_push(title, body, image=None):
    topic = "detection_1"
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        topic=topic
    )

    if image is not None:
        message.data = {
            "image_url": image
        }

    message_id = messaging.send(message)
    print('Successfully sent message:', message_id)


# Sample Response:
# send_topic_push("Penyakit Terdeteksi",
#                 "Ada penyakit pada tanaman anda",
#                 "https://www.yippeecode.com/wp-content/uploads/2022/10/Screen-Shot-2022-10-09-at-4.57.31-PM-1024x396.png"
#                 )
