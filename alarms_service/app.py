from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import time
import json
from threading import Thread
import datetime
from multiprocessing import Process
from sqlalchemy.exc import OperationalError
import logging


load_dotenv()  # Load environment variables from .env file

# Initialize Flask app
app = Flask(__name__)
app.config.from_object('config.Config')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy
from models import db, AlarmRule, SensorData, AlarmPushMQTT
db.init_app(app)

from mqtt_subscriber import MQTTSubscriber
from processor_alarm import ProcessorAlarm

# Define routes
@app.route('/')
def index():
    return render_template('index.html')

# @app.route('/create_alarm')
# def create_alarm():
#     return render_template('create_alarm.html')

# @app.route('/view_alarms')
# def view_alarms():
#     alarms = AlarmRule.query.all()
#     return render_template('view_alarms.html', alarms=alarms)


# @app.route('/alarm_pushes')
# def get_alarm_pushes():
#     # Get the page number and page size from query parameters
#     page = request.args.get('page', 1, type=int)
#     per_page = request.args.get('per_page', 10, type=int)
    
#     # Query for pushes with pagination
#     pushes_query = AlarmPushMQTT.query.paginate(page, per_page, False)
    
#     # Convert to list of dictionaries
#     pushes = [push.to_dict() for push in pushes_query.items]
    
#     # Create response object
#     response = {
#         'total': pushes_query.total,
#         'pages': pushes_query.pages,
#         'current_page': pushes_query.page,
#         'per_page': pushes_query.per_page,
#         'pushes': pushes
#     }
    
#     return jsonify(response)


# @app.route('/alarm_pushes')
# def get_alarm_pushes():
#     page = request.args.get('page', 1, type=int)
#     per_page = 20
    
#     # Order by timestamp in descending order
#     pagination = AlarmPushMQTT.query.order_by(AlarmPushMQTT.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
#     alarm_pushes = pagination.items
    
#     return jsonify({
#         'alarm_pushes': [log.to_dict() for log in alarm_pushes],
#         'total': pagination.total,
#         'pages': pagination.pages,
#         'current_page': pagination.page,
#         'has_next': pagination.has_next,
#         'has_prev': pagination.has_prev,
#         'next_num': pagination.next_num,
#         'prev_num': pagination.prev_num,
#         'iter_pages': list(pagination.iter_pages())  # This will give a list of page numbers
#     })


@app.route('/alarm_pushes')
def get_alarm_pushes():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Order by timestamp in descending order
    pagination = AlarmPushMQTT.query.order_by(AlarmPushMQTT.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    alarm_pushes = pagination.items
    
    return jsonify({
        'alarm_pushes': [log.to_dict() for log in alarm_pushes],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'next_num': pagination.next_num,
        'prev_num': pagination.prev_num,
        'iter_pages': list(pagination.iter_pages())
    })

@app.route('/alarm_rules/<int:rule_id>')
def view_alarm_rule(rule_id):
    rule = AlarmRule.query.get_or_404(rule_id)
    return render_template('view_alarm_rule.html', rule=rule)

@app.route('/alarm_rules', methods=['POST','GET'])
def alarm_rules():
    if request.method == 'POST':
        sensor_id_temp = request.form['sensor_id_temp']
        threshold_condition = request.form['threshold_condition']
        threshold_value = request.form['threshold_value']
        duration = request.form['duration']
        shunt_enabled = 'shunt_enabled' in request.form

        shunt_sensor_id = request.form['shunt_sensor_id'] if shunt_enabled else None
        shunt_threshold_condition = request.form['shunt_threshold_condition'] if shunt_enabled else None
        shunt_threshold_value = request.form['shunt_threshold_value'] if shunt_enabled else None

        alarm_rule = AlarmRule(
            sensor_id=sensor_id_temp,
            threshold_condition=threshold_condition,
            threshold_value=threshold_value,
            duration=duration,
            shunt_enabled=shunt_enabled,
            shunt_sensor_id=shunt_sensor_id,
            shunt_threshold_condition=shunt_threshold_condition,
            shunt_threshold_value=shunt_threshold_value,
            alarm_type="conditional" if shunt_enabled else "simple"
        )

        db.session.add(alarm_rule)
        db.session.commit()

        return redirect(url_for('alarm_rules'))
    
    alarms = AlarmRule.query.all()
    sensor_ids = [{"sensor_id":sensor.sensor_id,"sensor_type":sensor.sensor_type} for sensor in db.session.query(SensorData.sensor_id,SensorData.sensor_type).distinct()]
    return render_template('alarm.html', alarms=alarms, sensors=sensor_ids)

@app.route('/edit_alarm/<int:alarm_id>', methods=['GET', 'POST'])
def edit_alarm(alarm_id):
    alarm = AlarmRule.query.get_or_404(alarm_id)
    if request.method == 'POST':
        alarm.sensor_id = request.form['sensor_id']
        alarm.threshold_condition = request.form['threshold_condition']
        alarm.threshold_value = float(request.form['threshold_value'])
        alarm.duration = int(request.form['duration'])
        alarm.shunt_enabled = 'shunt_enabled' in request.form

        alarm.shunt_sensor_id = request.form.get('shunt_sensor_id') if alarm.shunt_enabled else None
        alarm.shunt_threshold_condition = request.form.get('shunt_threshold_condition') if alarm.shunt_enabled else None
        alarm.shunt_threshold_value = float(request.form.get('shunt_threshold_value')) if alarm.shunt_enabled else None

        db.session.commit()
        return redirect(url_for('alarm_rules'))

    sensor_ids = [{"sensor_id":sensor.sensor_id,"sensor_type":sensor.sensor_type} for sensor in db.session.query(SensorData.sensor_id,SensorData.sensor_type).distinct()]
    return render_template('edit_alarm.html', alarm=alarm, sensors=sensor_ids)


# @app.route('/delete_alarm/<int:alarm_id>')
# def delete_alarm(alarm_id):
#     alarm = AlarmRule.query.get_or_404(alarm_id)
#     db.session.delete(alarm)
#     db.session.commit()
#     return redirect(url_for('alarm_rules'))

@app.route('/delete_alarm/<int:alarm_id>', methods=['GET'])
def delete_alarm(alarm_id):
    try:
        # Find and delete related alarm pushes
        AlarmPushMQTT.query.filter_by(alarm_id=alarm_id).delete()

        # Find and delete the alarm rule
        alarm = AlarmRule.query.get(alarm_id)
        if not alarm:
            return "Alarm not found", 404

        db.session.delete(alarm)
        db.session.commit()

        return redirect('/alarm_rules')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting alarm: {e}")
        return "Internal Server Error", 500

@app.route('/view_sensors')
def view_sensors():
    # Fetch the latest entry for each sensor
    subquery = db.session.query(
        SensorData.sensor_id,
        db.func.max(SensorData.timestamp).label('max_timestamp')
    ).group_by(SensorData.sensor_id).subquery()

    latest_entries = db.session.query(
        SensorData.sensor_id,
        SensorData.sensor_type,
        SensorData.value,
        SensorData.timestamp
    ).join(
        subquery,
        (SensorData.sensor_id == subquery.c.sensor_id) & (SensorData.timestamp == subquery.c.max_timestamp)
    ).all()

    # Fetch distinct sensor IDs
    sensor_ids = [sensor.sensor_id for sensor in db.session.query(SensorData.sensor_id).distinct()]

    return render_template('view_sensors.html', latest_entries=latest_entries, sensor_ids=sensor_ids)


@app.route('/sensor_data', methods=['GET'])
def sensor_data():
    sensor_id = request.args.get('sensor_id')
    sensor_data = SensorData.query.filter_by(sensor_id=sensor_id).order_by(SensorData.timestamp.desc()).limit(20).all()
    data = [{'id': s.id, 'sensor_id': s.sensor_id, 'sensor_type': s.sensor_type, 'value': s.value, 'timestamp': s.timestamp} for s in sensor_data]
    return jsonify(data)


# MQTT and Processor initialization
def init_mqtt_subscriber():
    try:
        mqtt_subscriber = MQTTSubscriber(app)
        mqtt_subscriber.start()
        logger.info("MQTT Subscriber started successfully.")
    except Exception as e:
        logger.error(f"Error initializing MQTT Subscriber: {e}")

def init_alarm_processor():
    try:
        with app.app_context():
            alarm_processor = ProcessorAlarm(app, db)
            alarm_processor.start()
            logger.info("Alarm Processor started successfully.")
    except Exception as e:
        logger.error(f"Error initializing Alarm Processor: {e}")


# Initialize the app and start services
def create_app():
    connected = False
    while not connected:
        try:
            with app.app_context():
                db.create_all()
            connected = True
            logger.info("Database connection established successfully.")
        except OperationalError:
            logger.error("Database connection failed. Retrying in 5 seconds...")
            time.sleep(5)
    try:
        # Start MQTT client and processors in separate processes
        mqtt_subscriber_process = Process(target=init_mqtt_subscriber)
        alarm_processor_process = Process(target=init_alarm_processor)
        
        mqtt_subscriber_process.start()
        alarm_processor_process.start()
        logger.info("MQTT Subscriber and Alarm Processor processes started successfully.")
    except Exception as e:
        logger.error(f"Error starting processes: {e}")

    return app


if __name__ == '__main__':
    try:
        app = create_app()
        app.run(host='0.0.0.0', port=5002)
        logger.info("Flask application started successfully.")
    except Exception as e:
        logger.error(f"Error running Flask application: {e}")