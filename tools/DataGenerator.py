import datetime
import json
import os.path
import random
import time

BASE_PATH = path = os.path.dirname(os.path.dirname(__file__))


class SensorKey:
    """Unique key of a sensor"""

    def __init__(self, name: str):
        """Constructor"""
        self.name: str = name

class Sensor:
    """Sensor object, which stores all information of a given sensor."""

    def __init__(self, name: str, pressure: float | None, temperature: float | None, distance: float | None):
        """Constructor"""

        self.name: str = name
        self.pressure: float | None = pressure
        self.temperature: float | None = temperature
        self.distance: float | None = distance


class DataGenerator:
    """Data Generator, which provides and stores sensor data of a given satellite."""

    def __init__(self):
        """Constructor"""
        self.available_sensors: list[SensorKey] = [
            SensorKey(name="thruster_1.a"),
            SensorKey(name="oxygen_tank_1"),
            SensorKey(name="hydrogen_tank_1"),
        ]

    def generate_new_sensor_data(self):

        druckH = random.uniform(1.50, 3.50)
        temperaturH = random.uniform(14.00, 20.15)
        druckO = random.uniform(1.50, 3.50)
        temperaturO = random.uniform(90.00, 95.00)
        temperaturA = random.uniform(2800, 3500)
        druckA = random.uniform(1.0, 3.0)
        entfernung  = random.uniform(160.00, 2000.00)

        selected_key_idx = random.randint(0, len(self.available_sensors) - 1)
        selected_key = self.available_sensors[selected_key_idx]


        

        if selected_key.name == "hydrogen_tank_1": 
            sensor_data = Sensor(
                name=selected_key.name,
                pressure=druckH, 
                temperature=temperaturH,
                distance=entfernung 
        )
     
        elif selected_key.name == "oxygen_tank_1":
            sensor_data = Sensor(
                name=selected_key.name,
                pressure=druckO,
                temperature=temperaturO,
                distance=entfernung 
        )

        else:
            sensor_data = Sensor(
                name=selected_key.name,
                pressure=druckA,
                temperature=temperaturA,
                distance=entfernung
        )

        return sensor_data

    @staticmethod
    def store_sensor_data(data: Sensor):
        content = data.__dict__
        file_name = "/data/TM_" + datetime.datetime.now().isoformat() + ".json"
        with open(BASE_PATH + file_name, "w") as file:
            json.dump(content, file)


if __name__ == '__main__':
    generator = DataGenerator()

    while True:
        data = generator.generate_new_sensor_data()
        generator.store_sensor_data(data=data)
        print(f"Sucessfully stored: {data}")
        time.sleep(random.randint(1, 10))  # Sleep for a random time between 1 and 10 seconds