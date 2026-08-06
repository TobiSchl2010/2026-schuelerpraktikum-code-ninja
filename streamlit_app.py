# Import
import asyncio
import json

import pandas as pd
import streamlit as st
import websockets

BACKEND_URI = "ws://localhost:8000/ws"

# Anzeigenamen der Komponenten fuer die Tabelle
komponenten_namen = {
    "oxygen_tank_1": "Sauerstofftank",
    "hydrogen_tank_1": "Wasserstofftank",
    "thruster_1.a": "Triebwerk 1.A"
}

# Welche Messwerte angezeigt werden. Steuert Tabellenspalten UND Diagramme,
# damit eine neue Messgroesse nur hier ergaenzt werden muss.
MESSGROESSEN = [
    {"feld": "temperature", "spalte": "Temperatur (K)", "titel": "Temperatur"},
    {"feld": "pressure", "spalte": "Druck (bar)", "titel": "Druck"}
]

# Wie viele Datensaetze pro Sensor in der Tabelle stehen duerfen
MAX_ZEILEN_PRO_SENSOR = 3

# Hintergrundfarbe je Sensor, damit die Bloecke in der Tabelle auseinandergehen.
# Ein Blauton in drei Helligkeitsstufen (Stufen 250/350/450 der Blau-Ramp),
# von hell nach dunkel. Die Abstaende sind so gewaehlt, dass die Stufen sich
# sichtbar unterscheiden und die Schrift auf allen dreien lesbar bleibt -
# geprueft in hellem und dunklem Streamlit-Theme.
# Zuordnung folgt der alphabetischen Reihenfolge der Anzeigenamen
# (Sauerstofftank, Triebwerk 1.A, Wasserstofftank), weil die Tabelle so
# sortiert ist - dadurch laeuft die Abstufung von oben nach unten hell -> dunkel.
sensor_farben = {
    "oxygen_tank_1": "#86b6ef",
    "thruster_1.a": "#5598e7",
    "hydrogen_tank_1": "#2a78d6"
}

# Schriftfarbe fest setzen, sonst bleibt sie im Streamlit-Dark-Theme hell
# und waere auf den blauen Flaechen nicht mehr lesbar. Reines Schwarz statt
# #0b0b0b, weil die dunkelste Stufe sonst knapp unter 4.5:1 Kontrast liegt.
TABELLEN_SCHRIFT = "#000000"

# Schwarze Trennlinien, weil sie auf allen drei Blaustufen am deutlichsten
# stehen (schlechtester Kontrast 4.76:1 - weiss kaeme nur auf 2.11:1).
# Waagerechte Trenner markieren den Sensorwechsel und bleiben kraeftig.
TABELLEN_LINIE = "2px solid #000000"

# Senkrechte Spaltenlinien duenner - ueberall gleich, sie sind reine Struktur
# und sollen die Trenner nicht ueberdecken.
LINIE_SENKRECHT = "2px solid #000000"

# Unter der Kopfzeile eine kraeftige Linie, damit sich die Spaltentitel
# klar vom Datenbereich absetzen.
LINIE_KOPFZEILE = "3px solid #000000"

# Aussenrahmen ringsum gleich stark, damit die Tabelle als geschlossener
# Block steht.
LINIE_AUSSEN = "1px solid #000000"

# Beigegelber Hintergrund fuer die Kopfzeile. Hell genug, dass die schwarze
# Schrift auch im Dark-Theme lesbar bleibt (16.55:1), und farblich deutlich
# von den blauen Datenzeilen abgesetzt.
KOPFZEILE_HINTERGRUND = "#efe4c2"

# Einzug der Komponentennamen in der ersten Spalte
EINZUG_ERSTE_SPALTE = "12px"

# Leerzeichen vor der Spaltenueberschrift "Komponente", damit sie nicht weiter
# links steht als die Namen darunter. Geschuetzte Leerzeichen (\u00a0), weil
# st.table die Titel durch Markdown schickt: normale Leerzeichen werden am
# Anfang verschluckt, und ab vier Stueck macht Markdown einen Codeblock daraus.
KOPFZEILE_EINZUG = "\u00a0" * 3

# Leerzeichen hinter "Druck (bar)", damit die Ueberschrift nicht weiter rechts
# steht als die Zahlen darunter - die haben rechts 12px Abstand bekommen.
KOPFZEILE_ABSTAND = "\u00a0" * 3

# Abstand der Druckwerte zur rechten Kante. Die Zahlen stehen rechtsbuendig,
# mehr Abstand rechts schiebt sie also nach links.
ABSTAND_LETZTE_SPALTE = "12px"

# Senkrechte Linien durchgehend. Waagerecht wird nur getrennt, wo sich die
# Farbe aendert - innerhalb eines Sensorblocks grenzen ja gleiche Flaechen
# aneinander.
# Hinweis: st.dataframe kann das nicht, es zeichnet die Tabelle auf ein Canvas
# und uebernimmt vom Styler nur die Zellfarben. st.table rendert echtes HTML.
TABELLEN_STILE = [
    # Leerer Selektor = das Tabellenelement selbst, also der Aussenrahmen
    {"selector": "", "props": [
        ("border", LINIE_AUSSEN),
        ("border-collapse", "collapse")
    ]},
    {"selector": "th", "props": [
        ("background-color", KOPFZEILE_HINTERGRUND),
        ("color", "#000000"),
        ("font-weight", "700"),
        ("border-top", "none"),
        # Kopfzeile und erste Datenzeile haben verschiedene Farben
        ("border-bottom", LINIE_KOPFZEILE),
        ("border-left", LINIE_SENKRECHT),
        ("border-right", LINIE_SENKRECHT)
    ]},
    {"selector": "td", "props": [
        ("border-top", "none"),
        ("border-bottom", "none"),
        ("border-left", LINIE_SENKRECHT),
        ("border-right", LINIE_SENKRECHT),
        # Ziffern gleich breit, damit Messwerte und Uhrzeiten untereinander
        # buendig stehen
        ("font-variant-numeric", "tabular-nums")
    ]},

    # Die beiden aeusseren Spaltenkanten duenner als die Linien im Inneren.
    # Jeder Selektor einzeln, weil Streamlit den Tabellen-Praefix nur vorne
    # anhaengt - "th:first-child, td:first-child" wuerde die zweite Haelfte
    # zu einer Regel fuer alle Tabellen der Seite machen.
    {"selector": "th:first-child", "props": [("border-left", LINIE_AUSSEN)]},
    {"selector": "td:first-child", "props": [
        ("border-left", LINIE_AUSSEN),
        # Einzug fuer die Komponentennamen. Streamlit setzt die erste Spalte
        # bei border=False auf padding-left: 0, dadurch klebt der Text sonst
        # direkt an der Rahmenlinie.
        ("padding-left", EINZUG_ERSTE_SPALTE)
    ]},
    {"selector": "th:last-child", "props": [("border-right", LINIE_AUSSEN)]},
    {"selector": "td:last-child", "props": [
        ("border-right", LINIE_AUSSEN),
        # Letzte Spalte ist "Druck (bar)" - siehe MESSGROESSEN
        ("padding-right", ABSTAND_LETZTE_SPALTE)
    ]}
]

# In der Tabelle steht der Anzeigename, nicht der technische Schluessel
farben_nach_anzeigename = {
    komponenten_namen[schluessel]: farbe
    for schluessel, farbe in sensor_farben.items()
}

diagramm_platzhalter = st.empty()
# Eigener Platzhalter fuer Status-Meldungen: so ersetzt jede neue Meldung die
# alte, statt sich bei jedem Verbindungsversuch auf der Seite zu stapeln.
status_platzhalter = st.empty()


def zeitreihe(eintraege, feld, beschriftung):
    """Baut aus den Rohdaten einen DataFrame mit lesbarer Zeitachse."""
    df = pd.DataFrame({
        "Zeit": pd.to_datetime([e["timestamp"] for e in eintraege], format="ISO8601"),
        beschriftung: [e.get(feld) for e in eintraege]
    })
    # Aelteste Werte zuerst, damit das Diagramm von links nach rechts laeuft
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
    gehoert - nur beim Wechsel wird eine Linie gezogen.
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

        # Linie nur beim Wechsel auf einen neuen Sensor, also dort wo sich die
        # Farbe aendert. Die erste Zeile braucht keine, dort grenzt schon die
        # Kopfzeile an.
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
        # Ohne diesen Fall wuerde sort_values("Zeit") auf einem leeren
        # DataFrame abstuerzen - genau das passiert direkt nach dem Start,
        # solange die Datenbank noch leer ist.
        st.info("Noch keine Messwerte empfangen.")
        return

    # Erst nach Komponente (A-Z), innerhalb einer Komponente die neueste
    # Messung zuerst. Dadurch stehen die Messwerte eines Sensors als
    # zusammenhaengender Block untereinander - passend zur Einfaerbung.
    tabelle = pd.DataFrame(zeilen).sort_values(
        ["Komponente", "Zeit"],
        ascending=[True, False]
    )

    # Einfaerbung noch auf den echten Spaltennamen berechnen
    stile = tabelle_einfaerben(tabelle)

    # Spaltentitel fett. st.table rendert die Titel durch Markdown, deshalb
    # die Sternchen - reines CSS reicht nicht, weil Streamlit den Zellen
    # font-weight: normal mitgibt.
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
        # Streamlit zeichnet keine eigenen Linien - die kommen alle aus
        # TABELLEN_STILE, sonst lägen zwei Gitter uebereinander.
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

        # Spalte und Expander in einer Zeile kombiniert
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
            # Deckt beide Faelle ab: Backend laeuft noch nicht (Verbindung
            # abgelehnt) und Verbindung mittendrin verloren.
            status_platzhalter.warning(
                f"Keine Verbindung zu {BACKEND_URI}. Neuer Versuch in 2 Sekunden. "
                "Laeuft der Server? `uvicorn main:app --reload`"
            )
            await asyncio.sleep(2)


asyncio.run(stream_daten())
