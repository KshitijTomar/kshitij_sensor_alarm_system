import os

class Config:
    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USER','user')}:{os.getenv('DB_PASSWORD','password')}@{os.getenv('DB_HOST','localhost')}/{os.getenv('DB_NAME','alarms')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MQTT_BROKER = os.getenv('MQTT_BROKER','localhost')
    MQTT_PORT = int(os.getenv('MQTT_PORT','1883'))
