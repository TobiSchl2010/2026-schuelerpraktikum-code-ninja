# Import
import asyncio
import json

import pandas as pd
import streamlit as st
import websockets

BACKEND_URI = "ws://localhost:8000/ws"

komponenten_namen = {
    "oxygen_tank_1": "Sauerstofftank",
    "hydrogen_tank_1": "Wasserstofftank",
    "thruster_1.a": "Triebwerk 1.A"
}

MESSGROESSEN = [
    {"feld": "temperature", "spalte": "Temperatur (K)", "titel": "Temperatur"},
    {"feld": "pressure", "spalte": "Druck (bar)", "titel": "Druck"}
]

MAX_ZEILEN_PRO_SENSOR = 3

sensor_farben = {
    "oxygen_tank_1": "#86b6ef",
    "thruster_1.a": "#5598e7",
    "hydrogen_tank_1": "#2a78d6"
}

TABELLEN_SCHRIFT = "#000000"

TABELLEN_LINIE = "2px solid #000000"
LINIE_SENKRECHT = "2px solid #000000"
LINIE_KOPFZEILE = "3px solid #000000"
LINIE_AUSSEN = "1px solid #000000"
KOPFZEILE_HINTERGRUND = "#efe4c2"

EINZUG_ERSTE_SPALTE = "12px"
ABSTAND_LETZTE_SPALTE = "12px"

KOPFZEILE_EINZUG = " " * 3
KOPFZEILE_ABSTAND = " " * 3

TABELLEN_STILE = [
    {"selector": "", "props": [
        ("border", LINIE_AUSSEN),
        ("border-collapse", "collapse")
    ]},
    {"selector": "th", "props": [
        ("background-color", KOPFZEILE_HINTERGRUND),
        ("color", "#000000"),
        ("font-weight", "700"),
        ("border-top", "none"),
        ("border-bottom", LINIE_KOPFZEILE),
        ("border-left", LINIE_SENKRECHT),
        ("border-right", LINIE_SENKRECHT)
    ]},
    {"selector": "td", "props": [
        ("border-top", "none"),
        ("border-bottom", "none"),
        ("border-left", LINIE_SENKRECHT),
        ("border-right", LINIE_SENKRECHT),
        ("font-variant-numeric", "tabular-nums")
    ]},

    {"selector": "th:first-child", "props": [("border-left", LINIE_AUSSEN)]},
    {"selector": "td:first-child", "props": [
        ("border-left", LINIE_AUSSEN),
        ("padding-left", EINZUG_ERSTE_SPALTE)
    ]},
    {"selector": "th:last-child", "props": [("border-right", LINIE_AUSSEN)]},
    {"selector": "td:last-child", "props": [
        ("border-right", LINIE_AUSSEN),
        ("padding-right", ABSTAND_LETZTE_SPALTE)
    ]}
]

DIAGRAMM_TITEL_GROESSE = "19px"

DIAGRAMM_TITEL_STIL = f"""
    <style>
    [data-testid="stExpander"] summary p {{
        font-size: {DIAGRAMM_TITEL_GROESSE};
        font-weight: 600;
    }}
    </style>
"""

farben_nach_anzeigename = {
    komponenten_namen[schluessel]: farbe
    for schluessel, farbe in sensor_farben.items()
}

st.markdown(DIAGRAMM_TITEL_STIL, unsafe_allow_html=True)

diagramm_platzhalter = st.empty()
status_platzhalter = st.empty()


def zeitreihe(eintraege, feld, beschriftung):
    """Baut aus den Rohdaten einen DataFrame mit lesbarer Zeitachse."""
    df = pd.DataFrame({
        "Zeit": pd.to_datetime([e["timestamp"] for e in eintraege], format="ISO8601"),
        beschriftung: [e.get(feld) for e in eintraege]
    })
    return df.sort_values("Zeit").set_index("Zeit")


def neueste_eintraege(eintraege, anzahl=MAX_ZEILEN_PRO_SENSOR):
    """Liefert die juengsten Datensaetze einer Komponente, neuester zuerst.

    Kommt ein neuer Datensatz dazu, faellt damit automatisch der aelteste raus.
    """
    sortiert = sorted(
        eintraege,
        key=lambda e: pd.to_datetime(e["timestamp"], format="ISO8601"),
        reverse=True
    )
    return sortiert[:anzahl]


def gerundet(eintrag, feld):
    """Liest einen Messwert aus einem Datensatz und rundet ihn."""
    wert = eintrag.get(feld)
    return round(wert, 2) if wert is not None else None


def tabelle_einfaerben(tabelle):
    """Faerbt jede Zeile in der Farbe ihres Sensors und trennt die Bloecke.

    Arbeitet auf der ganzen Tabelle statt zeilenweise, weil fuer die
    Trennlinie bekannt sein muss, ob die Zeile darueber zum selben Sensor
    gehoert.
    """
    stile = pd.DataFrame("", index=tabelle.index, columns=tabelle.columns)
    vorherige_komponente = None

    for position, (zeilen_index, zeile) in enumerate(tabelle.iterrows()):
        komponente = zeile["Komponente"]
        regeln = []

        farbe = farben_nach_anzeigename.get(komponente)
        if farbe is not None:
            regeln.append(f"background-color: {farbe}")
            regeln.append(f"color: {TABELLEN_SCHRIFT}")

        if position > 0 and komponente != vorherige_komponente:
            regeln.append(f"border-top: {TABELLEN_LINIE}")

        stile.loc[zeilen_index] = "; ".join(regeln)
        vorherige_komponente = komponente

    return stile


def tabellen_zeilen_bauen(daten):
    """Sammelt die juengsten Messwerte aller Komponenten fuer die Tabelle."""
    zeilen = []
    for schluessel, anzeigename in komponenten_namen.items():
        for eintrag in neueste_eintraege(daten.get(schluessel, [])):
            zeile = {
                "Komponente": anzeigename,
                "Zeit": pd.to_datetime(eintrag["timestamp"], format="ISO8601")
            }
            for messgroesse in MESSGROESSEN:
                zeile[messgroesse["spalte"]] = gerundet(eintrag, messgroesse["feld"])
            zeilen.append(zeile)
    return zeilen


def tabelle_zeichnen(daten):
    """Zeigt die letzten Messwerte pro Sensor als eingefaerbte Tabelle."""
    st.subheader(f"Aktuelle Messwerte (letzte {MAX_ZEILEN_PRO_SENSOR} pro Sensor)")

    zeilen = tabellen_zeilen_bauen(daten)
    if not zeilen:
        st.info("Noch keine Messwerte empfangen.")
        return

    tabelle = pd.DataFrame(zeilen).sort_values(
        ["Komponente", "Zeit"],
        ascending=[True, False]
    )

    stile = tabelle_einfaerben(tabelle)

    fett = {}
    for spalte in tabelle.columns:
        titel = f"**{spalte}**"
        if spalte == "Komponente":
            titel = KOPFZEILE_EINZUG + titel
        elif spalte == MESSGROESSEN[-1]["spalte"]:
            titel = titel + KOPFZEILE_ABSTAND
        fett[spalte] = titel

    tabelle = tabelle.rename(columns=fett)
    stile = stile.rename(columns=fett)

    spalten_format = {fett["Zeit"]: lambda z: z.strftime("%Y-%m-%d %H:%M:%S")}
    for messgroesse in MESSGROESSEN:
        spalten_format[fett[messgroesse["spalte"]]] = "{:.2f}"

    st.table(
        tabelle.style
            .apply(lambda _: stile, axis=None)
            .format(spalten_format)
            .set_table_styles(TABELLEN_STILE),
        border=False,
        hide_index=True,
        width="stretch"
    )


def diagramme_zeichnen(daten):
    """Zeichnet pro Komponente eine Zeile mit einem Diagramm je Messgroesse."""
    st.subheader("Live-Diagramme")

    for schluessel, anzeigename in komponenten_namen.items():
        eintraege = daten.get(schluessel, [])
        spalten = st.columns(len(MESSGROESSEN))

        for spalte, messgroesse in zip(spalten, MESSGROESSEN):
            titel = f"{messgroesse['titel']} vom {anzeigename}"
            with spalte, st.expander(titel, expanded=True):
                df = zeitreihe(eintraege, messgroesse["feld"], messgroesse["spalte"])
                st.line_chart(
                    df,
                    x_label="Zeit (Uhrzeit)",
                    y_label=messgroesse["spalte"]
                )


def dashboard_zeichnen(daten):
    """Baut die komplette Seite neu auf."""
    with diagramm_platzhalter.container():
        st.title("Satellitendaten")
        tabelle_zeichnen(daten)
        diagramme_zeichnen(daten)


async def empfangen(websocket):
    """Lauscht auf Daten und zeichnet bei jedem Paket neu.

    Endet erst, wenn die Verbindung abbricht.
    """
    while True:
        daten_raw = await websocket.recv()
        dashboard_zeichnen(json.loads(daten_raw))


async def stream_daten():
    """Haelt die Verbindung zum Backend und baut sie bei Abbruch neu auf."""
    while True:
        try:
            async with websockets.connect(BACKEND_URI) as websocket:
                status_platzhalter.success("Erfolgreich mit Satelliten-Datenstrom verbunden!")
                await empfangen(websocket)

        except (OSError, websockets.exceptions.WebSocketException):
            status_platzhalter.warning(
                f"Keine Verbindung zu {BACKEND_URI}. Neuer Versuch in 2 Sekunden. "
                "Laeuft der Server? `uvicorn main:app --reload`"
            )
            await asyncio.sleep(2)


asyncio.run(stream_daten())
