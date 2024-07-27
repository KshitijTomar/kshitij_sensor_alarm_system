import paho.mqtt.client as mqtt
import os

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self):
        self.client.connect(os.getenv('MQTT_BROKER', 'localhost'), 1883, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker with result code " + str(rc))
        # client.subscribe("sensors/#")
        client.subscribe("sensor/data")

    # def on_message(self, client, userdata, msg):
    #     # Process incoming messages
    #     print(msg.topic + " " + str(msg.payload))
    #     # Pass the message to AlarmProcessor for evaluation if needed

    def on_message(self, client, userdata, msg):
        print(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
        # Call the ProcessorAlarm's on_message method
        if hasattr(client, 'processor_alarm'):
            client.processor_alarm.on_mqtt_message(client, userdata, msg)
        else:
            print("ProcessorAlarm instance not found in MQTT client")
