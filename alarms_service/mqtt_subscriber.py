import json
import paho.mqtt.client as mqtt
from models import db, SensorData
import os
import logging

class MQTTSubscriber:
    def __init__(self, app):
        self.app = app
        self.client = mqtt.Client()
        self.client.on_message = self.on_message
        self.client.connect(os.getenv('MQTT_BROKER'), int(os.getenv('MQTT_PORT')))
        self.client.subscribe('sensor/data')

        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        file_handler = logging.FileHandler('./_log_mqtt_subscriber.log')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # console_handler = logging.StreamHandler()
        # console_handler.setLevel(logging.INFO)
        # console_handler.setFormatter(formatter)
        # self.logger.addHandler(console_handler)

        self.logger.info('MQTTSubscriber initialized.')

    def on_message(self, client, userdata, message):
        try:
            data = json.loads(message.payload.decode())
            self.logger.info(f"Received message: {data}")
            sensor_id = data.get('sensor_id')
            # sensor_type, sensor_value = [(key, value) for key, value in data.items() if key != 'sensor_id'][0]
            for entry in [(key, value) for key, value in data.items() if key != 'sensor_id']:
                sensor_type, sensor_value = entry
                if sensor_id and sensor_type and sensor_value is not None:
                    with self.app.app_context():
                        sensor_data = SensorData(sensor_id=sensor_id, sensor_type=sensor_type, value=sensor_value)
                        db.session.add(sensor_data)
                        db.session.commit()
                        # self.logger.info(f"Data saved to DB: {sensor_id}, {sensor_type}, {sensor_value}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def start(self):
        self.logger.info('MQTT client starting loop...')
        self.client.loop_forever()