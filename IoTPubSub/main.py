import sys
import time
import json
import threading
import awsiot.greengrasscoreipc.clientv2 as clientV2

# Create an IPC client for subscribing and publishing to the IoT Core.
ipc_client = clientV2.GreengrassCoreIPCClientV2()
                    
def on_stream_event(event):
    # This function is called when a new message is received on the stream.
    try:
        topic = event.message.topic_name
        message = str(event.message.payload, 'utf-8')
        print(f'Received new message on topic {topic}:  {message}')
        
        # Prepare and publish a response message.
        publish_topic = f"{topic}/response"
        response_message = {
            "message": "Received your message",
            "original": message,
            "timestamp": time.time()
        }
        publish_message(publish_topic, json.dumps(response_message))
    except Exception as e:
        print(f"Error on_stream_event: {e}, Type: {type(e)}")

def on_stream_error(e):
    # Return True to close stream, False to keep stream open.
    print(f"Error on_stream_error: {e}, Type: {type(e)}")
    return False

def on_stream_closed():
    # This function is called when the stream is closed.
    print("Subscribe to topic stream closed")
    pass

def publish_message(topic, message):
    # Publishes a message to the IoT Core.
    try:
        print(f"Publishing message to topic: {topic}")
        ipc_client.publish_to_iot_core(topic_name=topic, qos='1', payload=bytes(message, "utf-8"))
        print("Message published successfully")
    except Exception as e:
        print(f"Error threaded_publish: {e}, Type: {type(e)}")

# Parse command-line arguments for the subscribe topic.
topic = sys.argv[1]
print(f"Subscribing to topic: {topic}")

# Subscribe to the specified topic.
resp, operation = ipc_client.subscribe_to_iot_core(
    topic_name=topic,
    qos='1', 
    on_stream_event=on_stream_event,
    on_stream_error=on_stream_error,
    on_stream_closed=on_stream_closed
)

# Keep the main thread alive, or the process will exit.
event = threading.Event()
event.wait()

# To stop subscribing, close the operation stream.
# operation.close()
# ipc_client.close()