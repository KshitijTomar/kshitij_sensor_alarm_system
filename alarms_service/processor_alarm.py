import time
import json
from threading import Thread
from models import AlarmRule, SensorData, AlarmPushMQTT
from mqtt_client import MQTTClient
from datetime import datetime, timedelta
import os
import logging

class ProcessorAlarm:
    def __init__(self, app, db):
        self.app = app
        self.db = db
        self.run_on_time = False

        self.mqtt_client = MQTTClient()
        self.mqtt_client.client.connect(os.getenv('MQTT_BROKER','localhost'), int(os.getenv('MQTT_PORT','1883')))
        self.mqtt_client.client.subscribe('sensor/data')
        self.mqtt_client.client.on_message = self.on_mqtt_message
        self.last_trigger_times = {} 
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        file_handler = logging.FileHandler('./_log_processor_alarm.log')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        self.logger.info('ProcessorAlarm initialized.')

    def start(self):
        if self.run_on_time:
            self.logger.info('Starting ProcessorAlarm in scheduled mode.')
            while True:
                with self.app.app_context():
                    self.process_alarms()
                time.sleep(5)
        else:
            self.logger.info('Starting ProcessorAlarm in MQTT listening mode.')
            self.mqtt_client.client.loop_forever()


    def on_mqtt_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
            self.logger.info(f"Received MQTT message: {data}")
            sensor_id = data.get('sensor_id')
            sensor_type, sensor_value = [(key, value) for key, value in data.items() if key != 'sensor_id'][0]
            if sensor_id and sensor_type and sensor_value is not None:
                sensor_data = SensorData(sensor_id=sensor_id, sensor_type=sensor_type, value=sensor_value, timestamp=datetime.utcnow())
                alarm_rules = AlarmRule.query.filter_by(sensor_id=sensor_data.sensor_id + ',' + sensor_data.sensor_type).all()
                for rule in alarm_rules:
                    if self.check_conditional_alarm(rule, sensor_data):
                        self.publish_alarm(rule)
        except json.JSONDecodeError:
            self.logger.error("Failed to decode MQTT message")
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}")
    
    def should_process_alarm(self, rule):
        last_trigger = self.last_trigger_times.get(rule.id, 0)
        current_time = time.time()
        # Determine if we need to check the alarm
        return (current_time - last_trigger) >= rule.duration * 60

    def process_alarms(self):
        alarm_rules = AlarmRule.query.all()
        for rule in alarm_rules:
            sensor_id=rule.sensor_id.split(',')[0]
            sensor_data = SensorData.query.filter_by(sensor_id=sensor_id).order_by(SensorData.timestamp.desc()).first()
            if sensor_data:
                if self.check_conditional_alarm(rule, sensor_data):
                    self.publish_alarm(rule)


    def check_conditional_alarm(self, rule, sensor_data):
        # Check if the conditional alarm condition is met
        threshold_exceeded = sensor_data.value > rule.threshold_value if rule.threshold_condition == '>' else sensor_data.value < rule.threshold_value
        if threshold_exceeded:
            shunt_condition_met = self.check_shunt_condition(rule)
            if shunt_condition_met:
                duration_exceeded = self.check_duration(rule, sensor_data)
                return duration_exceeded
        return False

    def check_shunt_condition(self, rule):
        if not rule.alarm_type == 'conditional':
            return True
        
        # Implement the logic to check shunt condition
        shunt_sensor_data = SensorData.query.filter_by(sensor_id=rule.shunt_sensor_id.split(',')[0]).order_by(SensorData.timestamp.desc()).first()
        
        if not shunt_sensor_data:
            return False

        if rule.shunt_threshold_condition == '>':
            return shunt_sensor_data.value > rule.shunt_threshold_value
        elif rule.shunt_threshold_condition == '<':
            return shunt_sensor_data.value < rule.shunt_threshold_value
        return False

    def check_duration(self, rule, sensor_data):
        # Get the end of the time window as a timestamp
        end_time = sensor_data.timestamp
        # Calculate the start time by subtracting the duration from the end time
        start_time = end_time - timedelta(minutes=rule.duration)

        # Fetch all sensor data entries within the time window
        sensor_data_entries = SensorData.query.filter(
            SensorData.sensor_id == rule.sensor_id.split(',')[0],
            SensorData.timestamp >= start_time,
            SensorData.timestamp <= end_time
        ).order_by(SensorData.timestamp).all()

        if len(sensor_data_entries) == 0:
            return False
        
        # Check if all fetched entries meet the rule condition
        for entry in sensor_data_entries:
            threshold_value = entry.value > rule.threshold_value if rule.threshold_condition == '>' else entry.value < rule.threshold_value
            if not threshold_value:
                return False
            
        return True



    def publish_alarm(self, rule):
        topic = f"alarms/{rule.sensor_id}"
        message = {
            "sensor_id": rule.sensor_id,
            "threshold_value": rule.threshold_value,
            "threshold_condition": rule.threshold_condition,
            "duration": rule.duration,
            "alarm_type": rule.alarm_type,
            "timestamp": time.time()
        }
        self.mqtt_client.client.publish(topic, json.dumps(message))
        self.alarm_push_to_mqtt(rule, message)

    def alarm_push_to_mqtt(self, rule, message):
        self.logger.info(f"Push alarm to MQTT: {rule.id}, {message}")
        alarm_push = AlarmPushMQTT(
            alarm_id=rule.id,
            message=json.dumps(message)
        )
        self.db.session.add(alarm_push)
        self.db.session.commit()
        
# Start the alarm processor in a separate thread
def start_alarm_processor(app,db):
    processor = ProcessorAlarm(app, db)
    thread = Thread(target=processor.start)
    thread.start()
