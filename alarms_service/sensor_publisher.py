import paho.mqtt.publish as publish
import os
import time
import json
import random

# MQTT settings from environment variables
broker = os.getenv('MQTT_BROKER', 'mqtt')
port = int(os.getenv('MQTT_PORT', 1883))
sensor_id = os.getenv('SENSOR_ID', 'sensor1')
min_value = float(os.getenv('MIN_VALUE', 15))
max_value = float(os.getenv('MAX_VALUE', 25))
sensor_type = os.getenv('TYPE', 'temperature')
current_min_value = float(os.getenv('CURRENT_MIN_VALUE', 10))
current_max_value = float(os.getenv('CURRENT_MAX_VALUE', 20))

# Function to generate random sensor value within a specified range
def generate_sensor_value(min_val, max_val):
    return round(random.uniform(min_val, max_val), 2)

# Function to generate a random current value within a specified range
def generate_current(min_val, max_val):
    return round(random.uniform(min_val, max_val), 2)

while True:
    try:
        data = {
            'sensor_id': sensor_id,
            sensor_type: generate_sensor_value(min_value, max_value),
            'current': generate_current(current_min_value, current_max_value)  # Using environment variables
        }
        publish.single('sensor/data', json.dumps(data), hostname=broker, port=port)
        print(f'Published data: {data}')
    except Exception as e:
        print(f'Error publishing data: {e}')
    time.sleep(5)
