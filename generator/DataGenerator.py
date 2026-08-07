import datetime
import json
import os.path
import random
import math

BASE_PATH = path = os.path.dirname(os.path.dirname(__file__))

# --- ECHTE WERTE DES SATELLITEN ---
UMLAUFZEIT = 5400.0   # Ein Umlauf um die Erde dauert 90 Minuten
STERNENTAG = 86164.0  # Eine Drehung der Erde dauert knapp 24 Stunden

OMEGA_S = 2 * math.pi / UMLAUFZEIT  # rad/s
OMEGA_E = 2 * math.pi / STERNENTAG  # rad/s

# --- ZEITRAFFER ---
# In Wirklichkeit dauert ein Umlauf 90 Minuten. So lange will beim
# Zuschauen niemand warten - man würde immer nur ein kurzes Stück
# der Bahn sehen und es sähe aus wie eine Linie.
#
# Deshalb läuft die Uhr der Simulation schneller. Nur die ZEIT wird
# gestreckt, die Bahn selbst bleibt physikalisch richtig.
#
# Hier einstellen, wie lange ein kompletter Umlauf auf dem Bildschirm
# dauern soll (in echten Sekunden). Größer = langsamer und ruhiger.
UMLAUF_ECHTZEIT = 240.0  # 4 Minuten für einen ganzen Ring um die Erde

ZEITRAFFER = UMLAUFZEIT / UMLAUF_ECHTZEIT  # = 22.5 fache Geschwindigkeit

# Fester Bezugspunkt für die Uhr der Simulation.
#
# Wichtig: Die Zeit wird NICHT beim Programmstart auf 0 gesetzt.
# Sonst würde der Satellit bei jedem Neustart des Servers wieder an
# derselben Stelle beginnen - und mit "uvicorn --reload" passiert das
# bei jedem Speichern. Genau das ließ ihn hin und her springen.
BEZUGSZEIT = datetime.datetime(
    2026, 1, 1, tzinfo=datetime.timezone.utc
).timestamp()

# Parameter für die Umlaufbahn (Beispielwerte, frei anpassbar)
INCLINATION_DEG = 50.0  # Bahnneigung in Grad (z.B. 50° Nord/Süd)
i = math.radians(INCLINATION_DEG)  # Inklination im Bogenmaß (Radiant)

# Höhen-Parameter (unter Berücksichtigung der Erdabplattung)
Z_0 = 500.0  # Durchschnittliche Höhe über dem Meeresspiegel in km
DELTA_Z = 10.7  # Amplitude der Schwankung (21.4 km Gesamtunterschied / 2)

# Startposition für den Längengrad (t = 0 am Nullmeridian)
X_0 = 0.0  

class SensorKey:
    """Unique key of a sensor"""

    def __init__(self, name: str, type: str):
        """Constructor"""
        self.name: str = name
        self.type: str = type


class Sensor:
    """Sensor object, which stores all information of a given sensor."""

    def __init__(self, name: str, type: str, pressure: float | None, temperature: float | None, x_deg: float | None, y_deg: float | None, z_km: float | None):
        """Constructor"""

        self.name: str = name
        self.type: str = type
        self.pressure: float | None = pressure
        self.temperature: float | None = temperature
        self.x_deg: float | None = x_deg
        self.y_deg: float | None = y_deg
        self.z_km: float | None = z_km


class DataGenerator:
    """Data Generator, which provides and stores sensor data of a given satellite."""

    def __init__(self):
        """Constructor"""
        self.available_sensors: list[SensorKey] = [
            SensorKey(name="thruster_1.a", type="thruster"),
            SensorKey(name="oxygen_tank_1", type="gas_valve"),
            SensorKey(name="hydrogen_tank_1", type="gas_valve")
        ]

    @staticmethod
    def simulationszeit():
        """
        Liefert die Uhrzeit der Simulation in Sekunden.

        Sie läuft um den ZEITRAFFER schneller als die echte Uhr und
        zählt ab einem festen Datum. Dadurch fliegt der Satellit nach
        einem Neustart des Servers einfach weiter, statt wieder von
        vorne anzufangen.
        """
        echte_sekunden = (
            datetime.datetime.now(datetime.timezone.utc).timestamp()
            - BEZUGSZEIT
        )

        return echte_sekunden * ZEITRAFFER

    @staticmethod
    def berechne_satelliten_koordinaten(t_sekunden):
        """
        Berechnet die x, y, z Koordinaten des Satelliten für einen Zeitpunkt t (in Sekunden).
        x = Längengrad (-180 bis +180 Grad)
        y = Breitengrad (-90 bis +90 Grad)
        z = Höhe über dem Meeresspiegel (in km)
        """
    
        # --- KOORDINATE Y: BREITENGRAD (Harmonische Schwingung) ---
        y_rad = math.asin(math.sin(i) * math.sin(OMEGA_S * t_sekunden))
        y_deg = math.degrees(y_rad)
    
        # --- KOORDINATE X: LÄNGENGRAD (Eigenbewegung + West-Drift durch Erdrotation) ---
        # math.atan2 liefert Werte von -pi bis +pi
        eigenbewegung_rad = math.atan2(
            math.cos(i) * math.sin(OMEGA_S * t_sekunden), 
            math.cos(OMEGA_S * t_sekunden)
        )
        erdrotation_rad = OMEGA_E * t_sekunden
    
        x_rad = eigenbewegung_rad - erdrotation_rad
        x_deg = math.degrees(x_rad) + X_0
    
        # Längengrad wieder mathematisch sauber in den Bereich -180 bis +180 Grad bringen
        x_deg = (x_deg + 180) % 360 - 180
    
        # --- KOORDINATE Z: HÖHE ÜBER DEM MEERESSPIEGEL (Doppelte Frequenz) ---
        # t=0 startet am Äquator (z ist minimal), nach 22.5 min (Pol) ist z maximal
        z_km = Z_0 - DELTA_Z * math.cos(2 * OMEGA_S * t_sekunden)
    
        return x_deg, y_deg, z_km


    def generate_new_sensor_data(self):

        selected_key_idx = random.randint(0, len(self.available_sensors) - 1)
        selected_key = self.available_sensors[selected_key_idx]

        #pressure = random.uniform(0.5, 9.0)
        #temperature = random.uniform(200.0, 500.0)

        x_deg, y_deg, z_km = self.berechne_satelliten_koordinaten(
            self.simulationszeit()
        )
        
        # 2. Standardabweichung (wie stark streuen die Werte im Schnitt?)
        sigma_grad = 0.02  # Typische Abweichung in Grad
        sigma_km = 0.1     # Typische Abweichung in Kilometern
        
        # 3. Zufallswerte addieren (gauss nutzt Mittelwert 0 und die Standardabweichung)
        x_deg += random.gauss(0, sigma_grad)
        y_deg += random.gauss(0, sigma_grad)
        z_km += random.gauss(0, sigma_km)


        if selected_key.name == "thruster_1.a":
            pressure = random.uniform(1.0, 3.0) # Bar
            temperature = random.uniform(2800, 3500) # Kelvin

            sensor_data = Sensor(
                name=selected_key.name,
                type=selected_key.type,
                pressure=pressure,
                temperature=temperature,
                x_deg=x_deg,
                y_deg=y_deg,
                z_km=z_km
            )
            

    
        elif selected_key.name == "oxygen_tank_1":
            pressure = random.uniform(1.50, 3.50) # Bar
            temperature = random.uniform(90.0, 95.0) # Kelvin

            sensor_data = Sensor(
                name=selected_key.name,
                type=selected_key.type,
                pressure=pressure,
                temperature=temperature,
                x_deg=x_deg,
                y_deg=y_deg,
                z_km=z_km
            )
        elif selected_key.name == "hydrogen_tank_1":
            pressure = random.uniform(1.50, 3.50) # Bar
            temperature = random.uniform(14.0, 20.15) # Kelvin

            sensor_data = Sensor(
                name=selected_key.name,
                type=selected_key.type,
                pressure=pressure,
                temperature=temperature,
                x_deg=x_deg,
                y_deg=y_deg,
                z_km=z_km
            )
        return sensor_data

    @staticmethod
    def store_sensor_data(data: Sensor):
        content = data.__dict__
        file_name = "/data/TM_" + datetime.datetime.now().isoformat() + ".json"
        with open(BASE_PATH + file_name, "w") as file:
            json.dump(content, file)





