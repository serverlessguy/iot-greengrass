import sys
import threading
import time
import json
import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.model import (
    QOS,
    SubscribeToIoTCoreRequest,
    SubscriptionResponseMessage,
    PublishToIoTCoreRequest
)

# Set a timeout for publish and subscribe operations.
TIMEOUT = 10

# Establish a connection with the AWS IoT Greengrass Core IPC.
ipc_client = awsiot.greengrasscoreipc.connect()

class IoTCoreMessageHandler:
    # Handles messages from AWS IoT Core.
    def __init__(self, publish_topic):
        # Topic to which responses will be published.
        self.publish_topic = publish_topic

    def on_stream_event(self, event: SubscriptionResponseMessage) -> None:
        # Handles incoming stream events from the subscribed topic.
        try:
            # Decode the message payload.
            message_string = event.message.payload.decode()
            message_topic = event.message.topic_name
            print(f"Received new message on topic: {message_topic}")
            print(f"Message: {message_string}")

            # Prepare and publish a response message.
            response_message = {
                "message": "Received your message",
                "original": message_string,
                "timestamp": time.time()
            }
            self.publish_message(json.dumps(response_message))
        except Exception as e:
            print(f"Exception in message handler: {e}, Type: {type(e)}")

    def publish_message(self, message):
        # Publishes a message to the IoT Core in a separate thread.
        thread = threading.Thread(target=self._threaded_publish, args=(message,))
        thread.start()

    def _threaded_publish(self, message):
        # Internal method to handle the message publishing in a separate thread.
        try:
            print(f"Publishing message to topic: {self.publish_topic}")
            request = PublishToIoTCoreRequest(
                topic_name=self.publish_topic,
                qos=QOS.AT_LEAST_ONCE,
                payload=bytes(message, "utf-8")
            )

            # Activate and wait for the publish operation to complete.
            publish_operation = ipc_client.new_publish_to_iot_core()
            publish_operation.activate(request)
            publish_operation.get_response().result(TIMEOUT)
            print("Message published successfully.")
        except Exception as e:
            print(f"Exception in publishing message: {e}, Type: {type(e)}")

    def on_stream_error(self, error: Exception) -> bool:
        print(f"Received an operation error: {error}, Type: {type(error)}")
        return False

    def on_stream_closed(self) -> None:
        print("Subscribe to IoT Core stream has been closed.")

def subscribe_to_topic(topic, publish_topic):
    # Subscribes to a specified topic.
    handler = IoTCoreMessageHandler(publish_topic)
    request = SubscribeToIoTCoreRequest(
        topic_name=topic,
        qos=QOS.AT_LEAST_ONCE
    )

    # Create and activate a new subscribe operation.
    subscribe_operation = ipc_client.new_subscribe_to_iot_core(handler)
    subscribe_operation.activate(request)

    # Wait for the subscribe operation to complete
    subscribe_operation.get_response().result(TIMEOUT)
    print(f"Successfully subscribed to {topic}")

def main():
    # Main function to handle the subscription and response logic.
    # Parse command-line arguments for the subscribe topic.
    subscribe_topic = sys.argv[1]
    publish_topic = f"{subscribe_topic}/response"
    print(f"Subscribing to topic: {subscribe_topic}")
    print(f"Publishing to topic: {publish_topic}")
    
    # Initiate subscription to the specified topic.
    subscribe_to_topic(subscribe_topic, publish_topic)

    # Keep the main thread alive to maintain the subscription.
    while True:
        time.sleep(10)

if __name__ == "__main__":
    main()
