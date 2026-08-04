import json
from pathlib import Path
import requests

from pydantic import ValidationError

from validation import Measurement


API_URL = "http://127.0.0.1:8000/data/"


def process_json_folder(folder):

    folder = Path(folder)

    for file in folder.glob("TM_*.json"):

        try:

            # Timestamp aus Dateiname holen
            timestamp = file.stem.replace("TM_", "")


            # JSON lesen
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)


            # Timestamp hinzufügen
            data["timestamp"] = timestamp


            # Validierung
            measurement = Measurement(**data)


            # Pydantic -> JSON
            json_data = measurement.model_dump(mode="json")

            print("Sende an API:")
            print(json_data)

            # POST Request an API
            answer = requests.post(
                API_URL,
                json=json_data
            )


            if answer.status_code == 201:
                print(
                    f"Gespeichert: {file.name}"
                )

            else:
                print(
                    f"API Fehler {file.name}: {answer.text}"
                )


        except ValidationError as e:

            print(
                f"Validierungsfehler {file.name}: {e}"
            )


        except requests.exceptions.RequestException as e:

            print(
                f"Request Fehler {file.name}: {e}"
            )


        except Exception as e:

            print(
                f"Unbekannter Fehler {file.name}: {e}"
            )