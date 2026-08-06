import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError

from database.database_access import collection
from processing.validation import Measurement


async def process_json_folder(folder):

    folder = Path(folder)

    for file in folder.glob("TM_*.json"):

        try:
            # 1. Zeitstempel aus Dateiname holen
            timestamp_str = file.stem.replace("TM_", "")
            
            # 2. String in echtes datetime-Objekt für Pydantic umwandeln
            # Beispiel-Format: 20260806_085100 -> %Y%m%d_%H%M%S
            try:
                timestamp_dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            except ValueError:
                # Fallback, falls Ihr Generator ISO-Format nutzt (z.B. 2026-08-06T08:51:00)
                timestamp_dt = datetime.fromisoformat(timestamp_str)

            # Datei asynchron oder klassisch einlesen
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Das echte datetime-Objekt in das Dict legen
            data["timestamp"] = timestamp_dt

            # Validierung über Pydantic
            measurement = Measurement(**data)
            json_data = measurement.model_dump(mode="json")

            # In MongoDB speichern
            await collection.insert_one(json_data)
            print(f"Erfolgreich in MongoDB gespeichert: {file.name}")

            # 3. KORREKTUR: Datei löschen, damit sie beim nächsten Durchlauf nicht wieder eingelesen wird
            file.unlink()

        except ValidationError as e:
            print(f"Validierungsfehler {file.name}: {e}")
            # Defekte Dateien wegsichern oder löschen, sonst blockieren sie die Schleife ewig
            file.unlink() 
        except Exception as e:
            print(f"Fehler bei Verarbeitung von {file.name}: {e}")