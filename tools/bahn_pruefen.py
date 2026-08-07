"""
Prüft, ob der Satellit eine ordentliche Umlaufbahn fliegt.

Das Skript liest die letzten Messungen aus der MongoDB und rechnet nach,
ob die Bahn stimmt. Damit kann man ohne Hinschauen feststellen, ob alles
in Ordnung ist.

Starten (Backend muss laufen):

    venv/bin/python tools/bahn_pruefen.py

Optional die Länge des Zeitfensters in Sekunden angeben:

    venv/bin/python tools/bahn_pruefen.py 300
"""

import asyncio
import math
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.database_access import collection  # noqa: E402
from generator.DataGenerator import UMLAUF_ECHTZEIT  # noqa: E402

# Wie viele Sekunden zurück geschaut wird
FENSTER = float(sys.argv[1]) if len(sys.argv) > 1 else 120.0

# Bahnneigung: so weit nach Norden und Süden sollte der Satellit kommen
ERWARTETE_BREITE = 50.0

BAUTEILE = ["thruster_1.a", "oxygen_tank_1", "hydrogen_tank_1"]


async def messungen_laden():
    """Holt die letzten Messungen mit Positionsangabe aus der Datenbank."""

    rohdaten = await collection.find(
        {"name": {"$in": BAUTEILE}},
        {"_id": 0, "timestamp": 1, "x_deg": 1, "y_deg": 1, "z_km": 1},
    ).sort("timestamp", -1).limit(1000).to_list(length=None)

    punkte = [p for p in rohdaten if p.get("x_deg") is not None]

    for p in punkte:
        p["zeit"] = (
            datetime.fromisoformat(p["timestamp"])
            if isinstance(p["timestamp"], str)
            else p["timestamp"]
        )

    punkte.sort(key=lambda p: p["zeit"])

    if not punkte:
        return []

    # Nur das gewünschte Zeitfenster behalten
    neueste = punkte[-1]["zeit"]

    return [
        p for p in punkte
        if (neueste - p["zeit"]).total_seconds() <= FENSTER
    ]


def pruefen(punkte):
    """Rechnet die Kennzahlen aus und meldet, was nicht stimmt."""

    if len(punkte) < 5:
        print("FEHLER: Zu wenige Messungen. Läuft das Backend?")
        return False

    spanne = (punkte[-1]["zeit"] - punkte[0]["zeit"]).total_seconds()

    # Schritte im Längengrad, immer über den kürzesten Weg
    schritte = [
        (b["x_deg"] - a["x_deg"] + 180) % 360 - 180
        for a, b in zip(punkte, punkte[1:])
    ]

    weg = sum(abs(s) for s in schritte)

    # Ein Rückwärts-Schritt heißt: Der Satellit springt zurück.
    # Genau das passiert, wenn mehrere Backends gleichzeitig laufen.
    rueckwaerts = [s for s in schritte if s < -0.05]

    breite_min = min(p["y_deg"] for p in punkte)
    breite_max = max(p["y_deg"] for p in punkte)

    # Aus der gemessenen Geschwindigkeit die Umlaufzeit hochrechnen
    umlauf_gemessen = 360.0 / (weg / spanne) if weg > 0 else 0

    print(f"Zeitfenster        : {spanne:.0f} s mit {len(punkte)} Messungen")
    print(f"Messabstand        : {spanne / (len(punkte) - 1):.1f} s")
    print(f"überstrichen       : {weg:.1f} Grad = {weg / 360:.2f} Umläufe")
    print(f"Umlaufzeit         : {umlauf_gemessen:.0f} s "
          f"(eingestellt: {UMLAUF_ECHTZEIT:.0f} s)")
    print(f"Breitengrad        : {breite_min:.1f} bis {breite_max:.1f} Grad")
    print(f"Höhe               : {min(p['z_km'] for p in punkte):.1f} bis "
          f"{max(p['z_km'] for p in punkte):.1f} km")
    print(f"Rückwärts-Sprünge  : {len(rueckwaerts)} von {len(schritte)}")
    print()

    fehler = []

    if rueckwaerts:
        fehler.append(
            f"Der Satellit springt {len(rueckwaerts)} mal zurück. "
            "Läuft mehr als ein Backend gleichzeitig? Prüfen mit: "
            "ps | grep -E 'uvicorn|multiprocessing-fork'"
        )

    # Toleranz, weil die Geschwindigkeit entlang der Bahn schwankt
    if not 0.6 * UMLAUF_ECHTZEIT < umlauf_gemessen < 1.8 * UMLAUF_ECHTZEIT:
        fehler.append(
            f"Die Umlaufzeit passt nicht zu UMLAUF_ECHTZEIT "
            f"({UMLAUF_ECHTZEIT:.0f} s). Wurde das Backend nach der "
            "Änderung neu gestartet? '--reload' tut das nicht ohne "
            "'pip install watchfiles'."
        )

    # Nur prüfen, wenn lange genug beobachtet wurde
    if spanne > UMLAUF_ECHTZEIT * 0.6 and breite_max - breite_min < 40:
        fehler.append(
            f"Der Satellit bleibt in einem schmalen Streifen "
            f"({breite_min:.0f} bis {breite_max:.0f} Grad). Erwartet sind "
            f"etwa -{ERWARTETE_BREITE:.0f} bis +{ERWARTETE_BREITE:.0f} Grad."
        )

    if fehler:
        for f in fehler:
            print("PROBLEM:", f)
        return False

    print("Alles in Ordnung: Der Satellit fliegt gleichmäßig in eine "
          "Richtung um die Erde.")
    return True


async def main():
    punkte = await messungen_laden()
    erfolgreich = pruefen(punkte)
    sys.exit(0 if erfolgreich else 1)


asyncio.run(main())
