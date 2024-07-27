from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class AlarmRule(db.Model):
    __tablename__ = 'alarm_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.String(100), nullable=False)
    threshold_condition = db.Column(db.String(10), nullable=False)
    threshold_value = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    shunt_enabled = db.Column(db.Boolean, default=False)
    shunt_sensor_id = db.Column(db.String(100), nullable=True)
    shunt_threshold_condition = db.Column(db.String(10), nullable=True)
    shunt_threshold_value = db.Column(db.Float, nullable=True)
    alarm_type = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'sensor_id': self.sensor_id,
            'threshold_condition': self.threshold_condition,
            'threshold_value': self.threshold_value,
            'duration': self.duration,
            'shunt_enabled': self.shunt_enabled,
            'shunt_sensor_id': self.shunt_sensor_id,
            'shunt_threshold_condition': self.shunt_threshold_condition,
            'shunt_threshold_value': self.shunt_threshold_value,
            'alarm_type': self.alarm_type,
        }

    
class SensorData(db.Model):
    __tablename__ = 'sensor_data'
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.String(50), nullable=False)
    sensor_type = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'sensor_id': self.sensor_id,
            'sensor_type': self.sensor_type,
            'value': self.value,
            'timestamp': self.timestamp
        }
    
class AlarmPushMQTT(db.Model):
    __tablename__ = 'alarm_pushes'
    id = db.Column(db.Integer, primary_key=True)
    alarm_id = db.Column(db.Integer, db.ForeignKey('alarm_rules.id'), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    message = db.Column(db.Text, nullable=False)
    alarm = db.relationship('AlarmRule', backref=db.backref('logs', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'alarm_id': self.alarm_id,
            'timestamp': self.timestamp,
            'message': self.message
        }
    