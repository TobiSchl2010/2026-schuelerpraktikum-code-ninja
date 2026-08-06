import datetime
import json
import os.path
import random
import time

BASE_PATH = path = os.path.dirname(os.path.dirname(__file__))


class SensorKey:
    """Unique key of a sensor"""

    def __init__(self, name: str, type: str):
        """Constructor"""
        self.name: str = name
        self.type: str = type


class Sensor:
    """Sensor object, which stores all information of a given sensor."""

    def __init__(self, name: str, type: str, pressure: float | None, temperature: float | None):
        """Constructor"""

        self.name: str = name
        self.type: str = type
        self.pressure: float | None = pressure
        self.temperature: float | None = temperature


class DataGenerator:
    """Data Generator, which provides and stores sensor data of a given satellite."""

    def __init__(self):
        """Constructor"""
        self.available_sensors: list[SensorKey] = [
            SensorKey(name="thruster_1.a", type="thruster"),
            SensorKey(name="thruster_1.b", type="thruster"),
            SensorKey(name="thruster_1.c", type="thruster"),
            SensorKey(name="thruster_2.a", type="thruster"),
            SensorKey(name="thruster_2.b", type="thruster"),
            SensorKey(name="thruster_2.c", type="thruster"),
            SensorKey(name="thruster_3.a", type="thruster"),
            SensorKey(name="thruster_3.b", type="thruster"),
            SensorKey(name="thruster_3.c", type="thruster"),
            SensorKey(name="oxygen_tank_1", type="gas_valve"),
            SensorKey(name="oxygen_tank_2", type="gas_valve"),
            SensorKey(name="hydrogen_tank_1", type="gas_valve"),
            SensorKey(name="hydrogen_tank_2", type="gas_valve")
        ]

    def generate_new_sensor_data(self):

        selected_key_idx = random.randint(0, len(self.available_sensors) - 1)
        selected_key = self.available_sensors[selected_key_idx]

        pressure = random.uniform(0.5, 9.0)
        temperature = random.uniform(200.0, 500.0)

        sensor_data = Sensor(
            name=selected_key.name,
            type=selected_key.type,
            pressure=pressure,
            temperature=temperature
        )

        return sensor_data

    @staticmethod
    def store_sensor_data(data: Sensor):
        content = data.__dict__
        file_name = "/data/TM_" + datetime.datetime.now().isoformat() + ".json"
        with open(BASE_PATH + file_name, "w") as file:
            json.dump(content, file)


