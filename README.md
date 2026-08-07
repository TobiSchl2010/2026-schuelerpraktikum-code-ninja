# QAware Schülerpraktikum 2026

Repository für das Schülerpraktikum 2026 bei QAware.

## Installation

### 1. Create and activate a virtual environment for your python packages of this project:

```shell
python3 -m venv venv
source venv/bin/activate
```

If you created a virtual environment, set it as python interpreter in your IDE.

- In IntelliJ:
  - Click on File -> Project Structure.
  - Add a new Python SDK of type Virtualenv environment -> existing environment.
  - Set the interpreter to the python that is located in the directory of your newly created virtual environment.
- In VSCode:
  - Click on View -> Command Palette.
  - Search for Python: Select Interpreter.
  - Select the interpreter that is located in the directory of your newly created virtual environment.

### 2. Install all dependencies:

```shell
pip install -r requirements.txt
```

### 3. Start the database:

```shell
docker compose up -d
```

### 4. Start the uvicorn backend:

```shell
uvicorn BeispielVerwaltung:app --reload
```

The `--reload` command is used to be able to update the code and start the application automatically.

### 5. Optional: Add the database to your IDE

#### IntelliJ

- Select the database menu on the right of the window. 
- Add a new data source via the '+' icon. 
- Select MongoDB as type and give your database a name. 
- Enter the credentials from the [docker-compose.yml](./docker-compose.yml) file and test the connection.

![database_access.png](images/database_access.png)

#### VSCode

- Install the MongoDB for VSCode extension: <https://marketplace.visualstudio.com/items?itemName=mongodb.mongodb-vscode>
- Click on the MongoDB icon on the left of the window.
- Click on "Add Connection" and enter the credentials from the [docker-compose.yml](./docker-compose.yml) file.

## Usage

After the installation the API can be called via curl or the browser to serve the user with data or as data storage.

For example: <http://127.0.0.1:8000/hello_world>

A more generalized overview of existing APIs can be retrieved in a Swagger UI under:
<http://127.0.0.1:8000/docs>

## Helpful Links

- [AsyncIOMotorClient – Connection to MongoDB](https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_client.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Git Documentation](https://git-scm.com/docs)

## Maintainer

T. Prade, <thomas.prade@qaware.de>
R. Kalleicher, <robin.kalleicher@qaware.de>
T. Werner, <thomas.werner@qaware.de>

## Initial Code and Idea

R. Kalleicher, <robin.kalleicher@qaware.de>
C. Thelen, <christoph.thelen@qaware.de>



## Ausführung

Um den ganzen Prozess laufen zu lassen, mache Folgendes Schritt für Schritt:

Terminal 1:
source venv/bin/activate
docker compose up -d

Terminal 2:
source venv/bin/activate
uvicorn main:app --reload

Terminal 3:
source venv/bin/activate
streamlit run streamlit_app.py

Dazwischen also jeweils ein neues Terminal erstellen!




















Einstieg — 0:20
„Unsere Daten laufen durch vier Stationen. Ein Generator schreibt Messwerte als JSON-Dateien. Die Verarbeitung prüft sie und legt sie in die Datenbank. Ein Websocket schiebt sie live nach außen. Streamlit zeichnet sie."


DataGenerator → JSON-Datei in data/ → Validierung → MongoDB → Websocket → Streamlit
Wichtig zu sagen: Backend und Frontend sind zwei getrennte Programme — FastAPI auf Port 8000, Streamlit auf Port 8501.

1. Processing + Validation — 1:30
processing/processing.py — die Fließbandarbeit (alle 2 Sekunden)

„process_json_folder schaut in den Ordner data und geht jede Datei durch, die TM_ im Namen hat."

Vier Schritte pro Datei:

Zeitstempel aus dem Dateinamen ziehen — nicht aus dem Inhalt. Erst wird das Format 20260807_103104 versucht, wenn das scheitert das ISO-Format als Rückfalllösung
Datei einlesen, Zeitstempel ins Dictionary legen
Validieren → Measurement(**data)
insert_one in MongoDB, dann file.unlink()
„Das Löschen ist entscheidend: Ohne das würde dieselbe Datei bei jedem Durchlauf wieder eingelesen und die Datenbank endlos vollgeschrieben."

Und der Punkt, der Betreuer freut:

„Auch eine kaputte Datei wird gelöscht. Sonst würde sie die Schleife für immer blockieren — jeder Durchlauf würde an derselben Datei scheitern."

processing/validation.py — der Türsteher

„Pydantic ist ein Bauplan. Wir schreiben hin, welche Felder es gibt und welchen Typ sie haben — timestamp ein Datum, name und type Text, dann fünf Zahlen: Temperatur, Druck und die drei Koordinaten."

Zwei Dinge macht Pydantic von allein:

Typen erzwingen und umwandeln — steht "92.1" als Text drin, wird eine Zahl daraus
Fehlende Felder ablehnen — alle Felder sind Pflicht
Dazu zwei eigene Regeln (field_validator):

Temperatur unter −273 °C → abgelehnt, das ist unter dem absoluten Nullpunkt, physikalisch unmöglich
Druck ≤ 0 → abgelehnt
„So kommt kein Unsinn in die Datenbank. Und wir merken einen Fehler beim Sensor sofort, statt ihn später im Diagramm zu suchen."

2. database_access — 1:10
„Hier liegt alles, was mit MongoDB zu tun hat — an einer Stelle, damit der Rest des Programms nichts über die Datenbank wissen muss."

Verbindung:

load_dotenv() holt Benutzer und Passwort aus der .env → keine Zugangsdaten im Code, die Datei ist in .gitignore
AsyncIOMotorClient — der asynchrone Mongo-Treiber. Wichtig, weil FastAPI asynchron arbeitet: Während die Datenbank antwortet, kann der Server andere Dinge tun statt zu warten
daten_laden() — drei Schritte:

find mit Filter: nur Komponenten aus unserer Liste
Projektion: nur die 7 Felder, die wir brauchen, _id ausdrücklich aus → weniger Daten über die Leitung
.sort("timestamp", -1).limit(100) → die 100 neuesten Messungen
Dann Umbau in eine Form, die das Frontend direkt nutzen kann:


{"oxygen_tank_1": [...], "thruster_1.a": [...], "hydrogen_tank_1": [...]}
„Nach Komponente gruppiert. Das Frontend fragt einfach daten['thruster_1.a'] und muss nicht selbst sortieren."

Am Ende der Datei steht if __name__ == "__main__" — damit lässt sich die Datenbank allein testen, ohne den ganzen Server zu starten.

3. Websocket + Streamlit — 1:40
Warum Websocket und nicht HTTP?

„Bei HTTP fragt der Browser, der Server antwortet, Verbindung zu. Für Live-Daten müsste man ständig neu fragen. Beim Websocket bleibt die Leitung offen — der Server schickt von sich aus, sobald es was Neues gibt."

api/websocket.py — die Verteilerstelle, drei kurze Funktionen:

clients — Liste aller verbundenen Zuschauer
connect → accept() und in die Liste
disconnect → aus der Liste
send_data → Broadcast: dieselben Daten an alle
„Wichtig: In send_data steht ein try/except. Ist ein Browser weg, wird der Client übersprungen und entfernt. Ohne das würde der Fehler die ganze Sende-Aufgabe beenden — dann bekäme niemand mehr Daten, obwohl der Server noch läuft."

main.py — was beim Start passiert. Der lifespan startet drei Dauer-Aufgaben:

Aufgabe	Takt	Job
generate_json_data	2 s	Generator schreibt JSON
process_json_data	2 s	JSON prüfen → MongoDB
daten_stream	1 s	DB lesen → an alle senden
Der Endpunkt @app.websocket("/ws") nimmt die Verbindung an und hält sie dann nur offen. Das Senden macht daten_stream, nicht der Endpunkt.

Wie Streamlit sich anhängt:

„Streamlit ist hier einfach ein Client, wie ein Browser. Es verbindet sich auf ws://localhost:8000/ws, wartet auf Pakete, wandelt den Text mit json.loads in ein Dictionary und zeichnet neu. Bricht die Verbindung ab, versucht es alle 2 Sekunden neu."

Der Satz, mit dem du punktest:

„Es sind eigentlich zwei Websockets hintereinander: Der Browser hängt an Streamlit auf Port 8501, und Streamlit hängt an FastAPI auf Port 8000. Streamlit ist gleichzeitig Server und Client."

Abschluss — 0:20
„Jede Schicht hat genau eine Aufgabe: Verarbeitung prüft, Datenbankschicht speichert und liest, Websocket verteilt, Streamlit zeigt. Man kann jede einzeln austauschen — eine andere Datenbank ändert nichts am Frontend."

Summe: 5:00. Falls du kürzen musst: die Tabelle in Abschnitt 3 weglassen (−20 s).

