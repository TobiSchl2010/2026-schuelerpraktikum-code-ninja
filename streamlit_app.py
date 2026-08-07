# Import
import asyncio
import json
import math
import random
import time
from collections import deque

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import websockets


# --------------------------------------------------
# Einstellungen
# --------------------------------------------------

ERDRADIUS = 6371

# Wie oft die Umlaufbahn neu gezeichnet wird (in Sekunden).
# Kleiner Wert = flüssigere Bewegung, aber mehr Rechenarbeit.
BILD_INTERVALL = 0.25

# Falls noch keine Messung bekannt ist: so lange dauert ein Positionswechsel.
STANDARD_UEBERGANG = 6.0

# Länger als das wird nie zwischen zwei Positionen geglitten.
MAX_UEBERGANG = 15.0

# Der Übergang dauert etwas länger als die letzte Messpause.
# Dadurch ist der Satellit fast immer in Bewegung und bleibt nicht
# kurz stehen, bevor die nächste Messung kommt.
UEBERGANG_ZUSCHLAG = 1.25

# So viele Punkte behält die Flugbahn (ältere werden vergessen).
#
# Ein kompletter Umlauf ist etwa 43000 km lang.
# 900 Punkte x 55 km = 49500 km - die Spur reicht also für einen
# ganzen Ring um die Erde. Mit den alten Werten (700 x 20 km =
# 14000 km) war nur ein Drittel davon zu sehen, egal wie lange man
# gewartet hat.
MAX_BAHN_PUNKTE = 900

# Erst wenn der Satellit so viele km geflogen ist, wird ein Bahnpunkt gespeichert.
MIN_BAHN_ABSTAND = 55

# Größe des Satellitenmodells in km (nur zur Darstellung, nicht echt).
SATELLIT_GROESSE = 900


# Speichert die echte Flugbahn.
#
# Sie liegt im session_state, damit sie einen Neustart des Skripts
# übersteht (zum Beispiel wenn die Verbindung neu aufgebaut wird
# oder der Browser die Seite neu lädt).
if "flugbahn" not in st.session_state:

    st.session_state["flugbahn"] = deque(
        maxlen=MAX_BAHN_PUNKTE
    )


flugbahn_punkte = st.session_state["flugbahn"]


# --------------------------------------------------
# Kamera (3D Ansicht)
# --------------------------------------------------

# Hier steht die Kamera beim Start.
# Kleinere Werte = näher dran.
#
# WICHTIG: Danach wird die Kamera vom Programm nie mehr angefasst.
# Drehen und Zoomen macht allein der Browser. Das ist der Grund,
# warum die Bewegung flüssig bleibt: Es gibt dabei keinen einzigen
# Neustart des Skripts.
KAMERA_START = dict(

    eye=dict(
        x=0.62,
        y=0.62,
        z=0.34
    ),


    # Die Kamera schaut auf die Erdmitte
    center=dict(
        x=0,
        y=0,
        z=0
    ),


    up=dict(
        x=0,
        y=0,
        z=1
    ),


    projection=dict(
        type="perspective"
    )
)


# Mit diesen Einstellungen kann man im Diagramm herumfliegen:
# Mausrad zoomt, die Werkzeugleiste ist immer sichtbar.
#
# Das läuft alles direkt im Browser. Es sind ausdrücklich KEINE
# Streamlit-Bedienelemente (Regler, Knöpfe) für die Kamera erlaubt:
# Jeder Klick darauf würde das Skript neu starten und damit die
# Verbindung zum Satelliten mitten im Betrieb abreißen lassen.
DIAGRAMM_BEDIENUNG = {

    # Zoomen mit dem Mausrad
    "scrollZoom": True,

    # Werkzeugleiste immer sichtbar (Drehen, Verschieben,
    # Zoomen, Ansicht zurücksetzen, Bild speichern)
    "displayModeBar": True,

    "displaylogo": False,

    # Doppelklick setzt die Ansicht zurück
    "doubleClick": "reset",

    "responsive": True,

    "toImageButtonOptions": {
        "filename": "umlaufbahn",
        "scale": 2
    }
}


# Anzeigenamen der Komponenten fuer die Tabelle
komponenten_namen = {
    "oxygen_tank_1": "Sauerstofftank",
    "hydrogen_tank_1": "Wasserstofftank",
    "thruster_1.a": "Triebwerk 1.A"
}


# --------------------------------------------------
# Aussehen der Tabelle
# --------------------------------------------------

# Diese Spalten zeigt die Tabelle (Feld in den Daten, Spaltenname)
MESSGROESSEN = [
    {"feld": "temperature", "spalte": "Temperatur (K)", "titel": "Temperatur"},
    {"feld": "pressure", "spalte": "Druck (bar)", "titel": "Druck"}
]

# So viele Messungen zeigt die Tabelle pro Sensor.
# Kommt eine neue dazu, faellt die aelteste heraus.
MAX_ZEILEN_PRO_SENSOR = 3

# Jeder Sensor hat seine eigene Zeilenfarbe
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

KOPFZEILE_EINZUG = " " * 3
KOPFZEILE_ABSTAND = " " * 3

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

# Fehlt ein Messwert, steht dieses Zeichen in der Zelle.
#
# Ohne das stürzt die Tabelle ab: "{:.2f}".format(None) wirft
# TypeError: unsupported format string passed to NoneType.__format__
FEHLENDER_WERT = "-"

# Die Zeilenfarben werden über den Anzeigenamen gesucht,
# weil in der Tabelle nicht der Schlüssel steht.
farben_nach_anzeigename = {
    komponenten_namen[schluessel]: farbe
    for schluessel, farbe in sensor_farben.items()
}


# Beschreibung der Live-Diagramme:
# (Schlüssel der Komponente, Messfeld, Titel, Beschriftung der Y-Achse)
diagramm_beschreibung = [
    ("oxygen_tank_1", "temperature", "Temperatur vom Sauerstofftank", "Temperatur (K)"),
    ("oxygen_tank_1", "pressure", "Druck vom Sauerstofftank", "Druck (bar)"),
    ("hydrogen_tank_1", "temperature", "Temperatur vom Wasserstofftank", "Temperatur (K)"),
    ("hydrogen_tank_1", "pressure", "Druck vom Wasserstofftank", "Druck (bar)"),
    ("thruster_1.a", "temperature", "Temperatur vom Triebwerk 1.A", "Temperatur (K)"),
    ("thruster_1.a", "pressure", "Druck vom Triebwerk 1.A", "Druck (bar)")
]


# Position der einzelnen Teile in der 3D Figur.
# Die Figur wird nur EINMAL gebaut, danach werden nur noch diese
# Teile aktualisiert. Deshalb muss die Reihenfolge bekannt sein.
TEIL_BAHN = 2
TEIL_BAHN_NEU = 3
TEIL_LOT = 4
TEIL_BODENPUNKT = 5
TEIL_RING = 6
TEIL_MARKER = 7
TEIL_BESCHRIFTUNG = 8
TEIL_KOERPER = 9
TEIL_PANEL_LINKS = 10
TEIL_PANEL_RECHTS = 11

# So weit über dem Satelliten steht seine Beschriftung (in km)
BESCHRIFTUNG_ABSTAND = 1600


# So viele Bahnpunkte direkt hinter dem Satelliten werden hell
# gezeichnet. Das zeigt, aus welcher Richtung er kommt.
HELLE_BAHN_PUNKTE = 150


# --------------------------------------------------
# GPS Koordinaten -> 3D Koordinaten
# --------------------------------------------------

def geo_to_xyz(lon_deg, lat_deg, altitude_km):
    """
    Wandelt:
    - Längengrad
    - Breitengrad
    - Höhe

    in kartesische XYZ-Koordinaten um.
    """

    radius = ERDRADIUS + altitude_km

    lon = math.radians(lon_deg)
    lat = math.radians(lat_deg)

    x = radius * math.cos(lat) * math.cos(lon)
    y = radius * math.cos(lat) * math.sin(lon)
    z = radius * math.sin(lat)

    return x, y, z



# --------------------------------------------------
# Bewegung weich machen
# --------------------------------------------------

def winkel_differenz(von_deg, nach_deg):
    """
    Kürzester Weg zwischen zwei Längengraden.

    Beispiel: von 179° nach -179° sind nur 2° und nicht 358°.
    """

    return (nach_deg - von_deg + 180) % 360 - 180



def zwischenposition(von, nach, anteil):
    """
    Berechnet eine Position zwischen zwei GPS-Positionen.

    anteil = 0   -> genau "von"
    anteil = 0.5 -> genau in der Mitte
    anteil = 1   -> genau "nach"

    Dadurch springt der Satellit nicht von Messung zu Messung,
    sondern gleitet weich dorthin.
    """

    von_lon, von_lat, von_hoehe = von
    nach_lon, nach_lat, nach_hoehe = nach

    lon = von_lon + winkel_differenz(von_lon, nach_lon) * anteil
    lat = von_lat + (nach_lat - von_lat) * anteil
    hoehe = von_hoehe + (nach_hoehe - von_hoehe) * anteil

    # Längengrad wieder in den Bereich -180 bis 180 bringen
    lon = (lon + 180) % 360 - 180

    return lon, lat, hoehe



# --------------------------------------------------
# Sterne
# --------------------------------------------------

def sterne(
    anzahl=500,
    radius=18000,
    freier_bereich=9000
):
    """
    Erstellt zufällig verteilte Sterne.
    """

    zufall = random.Random(42)

    x = []
    y = []
    z = []
    groessen = []


    while len(x) < anzahl:

        px = zufall.uniform(-radius, radius)
        py = zufall.uniform(-radius, radius)
        pz = zufall.uniform(-radius, radius)


        if math.sqrt(
            px ** 2 +
            py ** 2 +
            pz ** 2
        ) < freier_bereich:
            continue


        x.append(round(px))
        y.append(round(py))
        z.append(round(pz))

        groessen.append(
            zufall.choice(
                [
                    1,
                    1,
                    1,
                    1,
                    1.5,
                    2
                ]
            )
        )


    return x, y, z, groessen



# --------------------------------------------------
# Erde
# --------------------------------------------------

def erde(
    radius=ERDRADIUS,
    aufloesung=32
):

    laengengrade = [
        2 * math.pi * i / aufloesung
        for i in range(aufloesung + 1)
    ]

    breitengrade = [
        math.pi * j / aufloesung
        for j in range(aufloesung + 1)
    ]


    x = [
        [
            round(
                radius *
                math.sin(b) *
                math.cos(l),
                1
            )
            for l in laengengrade
        ]
        for b in breitengrade
    ]


    y = [
        [
            round(
                radius *
                math.sin(b) *
                math.sin(l),
                1
            )
            for l in laengengrade
        ]
        for b in breitengrade
    ]


    z = [
        [
            round(
                radius *
                math.cos(b),
                1
            )
            for _ in laengengrade
        ]
        for b in breitengrade
    ]


    return go.Surface(
        x=x,
        y=y,
        z=z,

        colorscale=[
            [0, "#0a2a5e"],
            [0.5, "#1565C0"],
            [1, "#0a2a5e"]
        ],

        showscale=False,
        hoverinfo="skip",
        name="Erde",

        lighting=dict(
            ambient=0.4,
            diffuse=0.9,
            specular=0.1
        ),

        lightposition=dict(
            x=30000,
            y=30000,
            z=15000
        )
    )



# --------------------------------------------------
# Quader für Satellit
# --------------------------------------------------

def lokale_achsen(position):
    """
    Liefert drei Richtungen am Ort des Satelliten:

    - oben: vom Erdmittelpunkt weg
    - ost:  waagerecht, quer zur Erdachse
    - nord: rechtwinklig zu den beiden anderen

    Damit steht der Satellit immer richtig im Raum und nicht
    schräg in der Luft.
    """

    x, y, z = position

    laenge = math.sqrt(x * x + y * y + z * z) or 1.0

    oben = (
        x / laenge,
        y / laenge,
        z / laenge
    )


    waagerecht = math.sqrt(x * x + y * y) or 1.0

    ost = (
        -y / waagerecht,
        x / waagerecht,
        0.0
    )


    # Kreuzprodukt aus oben und ost
    nord = (
        oben[1] * ost[2] - oben[2] * ost[1],
        oben[2] * ost[0] - oben[0] * ost[2],
        oben[0] * ost[1] - oben[1] * ost[0]
    )


    return oben, ost, nord



def quader_punkte(
    mittelpunkt,
    achsen,
    halbe_kanten
):
    """
    Berechnet die 8 Eckpunkte eines Quaders.

    halbe_kanten = (nach Osten, nach Norden, nach oben)
    """

    oben, ost, nord = achsen

    h_ost, h_nord, h_oben = halbe_kanten


    x = []
    y = []
    z = []


    for s_ost in (-1, 1):
        for s_nord in (-1, 1):
            for s_oben in (-1, 1):

                for achse, liste in (
                    (0, x),
                    (1, y),
                    (2, z)
                ):

                    liste.append(
                        mittelpunkt[achse] +
                        s_ost * h_ost * ost[achse] +
                        s_nord * h_nord * nord[achse] +
                        s_oben * h_oben * oben[achse]
                    )


    return x, y, z



def quader(
    farbe,
    name,
    in_legende=False
):
    """
    Leerer Quader. Die Eckpunkte werden später gesetzt.
    """

    return go.Mesh3d(
        x=[],
        y=[],
        z=[],

        alphahull=0,

        color=farbe,

        flatshading=True,

        hoverinfo="skip",

        name=name,

        showlegend=in_legende
    )



# --------------------------------------------------
# Satellit
# --------------------------------------------------

def satelliten_teile(
    position,
    groesse=SATELLIT_GROESSE
):
    """
    Eckpunkte für Körper und die beiden Solarpanels.
    """

    achsen = lokale_achsen(position)


    koerper = quader_punkte(
        position,
        achsen,

        (
            groesse * 0.28,
            groesse * 0.28,
            groesse * 0.28
        )
    )


    # Panels sitzen links und rechts vom Körper (in Ost-Richtung)
    ost = achsen[1]

    abstand = groesse * 0.95


    panel_links = quader_punkte(

        (
            position[0] - abstand * ost[0],
            position[1] - abstand * ost[1],
            position[2] - abstand * ost[2]
        ),

        achsen,

        (
            groesse * 0.55,
            groesse * 0.28,
            groesse * 0.04
        )
    )


    panel_rechts = quader_punkte(

        (
            position[0] + abstand * ost[0],
            position[1] + abstand * ost[1],
            position[2] + abstand * ost[2]
        ),

        achsen,

        (
            groesse * 0.55,
            groesse * 0.28,
            groesse * 0.04
        )
    )


    return koerper, panel_links, panel_rechts



# --------------------------------------------------
# 3D Umlaufbahn
# --------------------------------------------------

@st.cache_resource(show_spinner=False)
def hintergrund():
    """
    Sterne und Erde ändern sich nie.

    Deshalb werden sie nur ein einziges Mal berechnet und danach
    immer wieder verwendet. Das macht das Neuzeichnen viel schneller.
    """

    stern_x, stern_y, stern_z, stern_groessen = sterne()


    sterne_trace = go.Scatter3d(
        x=stern_x,
        y=stern_y,
        z=stern_z,

        mode="markers",

        marker=dict(
            size=stern_groessen,
            color="white",
            opacity=0.45
        ),

        hoverinfo="skip",

        showlegend=False
    )


    return sterne_trace, erde()



def erstelle_umlaufbahn():
    """
    Baut die komplette 3D Ansicht EINMAL auf:
    - Sterne
    - Erde
    - Flugbahn
    - Lot zur Erde + Bodenpunkt
    - Satellit (Leuchten, Marker, Körper, Panels)

    Die Daten sind noch leer und werden später von
    aktualisiere_umlaufbahn() gefüllt.
    """

    fig = go.Figure()


    # Sterne und Erde
    sterne_trace, erde_trace = hintergrund()

    fig.add_trace(sterne_trace)
    fig.add_trace(erde_trace)


    # Die schon geflogene Bahn (dunkel)
    fig.add_trace(
        go.Scatter3d(
            x=[],
            y=[],
            z=[],

            mode="lines",

            line=dict(
                color="#4FC3F7",
                width=2
            ),

            hoverinfo="skip",

            name="Flugbahn"
        )
    )


    # Das letzte Stück der Bahn in der Farbe des Satelliten.
    # So sieht man sofort, aus welcher Richtung er kommt.
    fig.add_trace(
        go.Scatter3d(
            x=[],
            y=[],
            z=[],

            mode="lines",

            line=dict(
                color="#FFD54F",
                width=5
            ),

            hoverinfo="skip",

            name="Zuletzt geflogen"
        )
    )


    # Lot: senkrechte Linie vom Satelliten zur Erdoberfläche
    fig.add_trace(
        go.Scatter3d(
            x=[],
            y=[],
            z=[],

            mode="lines",

            line=dict(
                color="#FFD54F",
                width=2,
                dash="dot"
            ),

            opacity=0.5,

            hoverinfo="skip",

            showlegend=False
        )
    )


    # Punkt auf der Erde, über dem der Satellit gerade steht
    fig.add_trace(
        go.Scatter3d(
            x=[],
            y=[],
            z=[],

            mode="markers",

            marker=dict(
                size=5,
                color="#FFD54F",
                opacity=0.8,

                symbol="circle-open"
            ),

            hoverinfo="skip",

            name="Punkt über der Erde"
        )
    )


    # Ring um den Satelliten, damit er zwischen den Sternen
    # sofort auffällt
    fig.add_trace(
        go.Scatter3d(
            x=[],
            y=[],
            z=[],

            mode="markers",

            marker=dict(
                size=26,
                color="#FFC107",

                symbol="circle-open"
            ),

            hoverinfo="skip",

            showlegend=False
        )
    )


    # Heller Marker in der Mitte
    fig.add_trace(
        go.Scatter3d(
            x=[],
            y=[],
            z=[],

            mode="markers",

            marker=dict(
                size=12,
                color="#FFEB3B",

                line=dict(
                    color="white",
                    width=2
                )
            ),

            customdata=[[0.0, 0.0, 0.0]],

            hovertemplate=(
                "<b>Satellit</b><br>"
                "Längengrad: %{customdata[0]:.2f}°<br>"
                "Breitengrad: %{customdata[1]:.2f}°<br>"
                "Höhe: %{customdata[2]:.1f} km"
                "<extra></extra>"
            ),

            name="Satellit"
        )
    )


    # Beschriftung (steht etwas über dem Satelliten)
    fig.add_trace(
        go.Scatter3d(
            x=[],
            y=[],
            z=[],

            mode="text",

            text=["Satellit"],

            textposition="middle center",

            textfont=dict(
                color="#FFEB3B",
                size=14
            ),

            hoverinfo="skip",

            showlegend=False
        )
    )


    # Körper und Solarpanels
    fig.add_trace(
        quader(
            "#ECEFF1",
            "Satellitenkörper"
        )
    )

    fig.add_trace(
        quader(
            "#1A237E",
            "Solarpanel"
        )
    )

    fig.add_trace(
        quader(
            "#1A237E",
            "Solarpanel"
        )
    )


    # Achsen verstecken

    achse_unsichtbar = dict(

        visible=False,

        showgrid=False,

        zeroline=False,

        showbackground=False,

        showticklabels=False,

        title=""
    )



    fig.update_layout(

        # Mehr Höhe = mehr Platz zum Drehen und Zoomen
        height=560,

        margin=dict(
            l=0,
            r=0,
            t=0,
            b=0
        ),

        paper_bgcolor="black",

        font=dict(
            color="white"
        ),


        # uirevision sorgt dafür, dass die selbst gedrehte und
        # gezoomte Ansicht beim Aktualisieren erhalten bleibt.
        #
        # Der Wert muss dafür IMMER gleich bleiben. Würde er sich
        # ändern, würde die Kamera viermal pro Sekunde zurück auf
        # den Startwert springen - Zoomen wäre dann unmöglich.
        uirevision="umlaufbahn",


        legend=dict(
            bgcolor="rgba(0,0,0,0)"
        ),


        scene=dict(

            bgcolor="black",

            aspectmode="data",

            uirevision="umlaufbahn",


            # "turntable" dreht die Ansicht wie einen Globus.
            # Sie kann dabei nie auf den Kopf kippen.
            # (In der Werkzeugleiste gibt es auch freies Drehen.)
            dragmode="turntable",

            xaxis=achse_unsichtbar,

            yaxis=achse_unsichtbar,

            zaxis=achse_unsichtbar,


            camera=KAMERA_START
        )
    )


    return fig



def aktualisiere_umlaufbahn(
    fig,
    position,
    flugbahn,
    bild_nummer
):
    """
    Setzt nur die Teile neu, die sich bewegt haben.

    Sterne und Erde bleiben unverändert - dadurch ruckelt das Bild
    beim Aktualisieren nicht mehr.
    """

    # Streamlit beschwert sich, wenn zweimal genau das gleiche
    # Diagramm gezeichnet wird. Die Bildnummer ist unsichtbar und
    # macht jedes Bild eindeutig.
    fig.layout.meta = bild_nummer


    lon, lat, hoehe = position

    x, y, z = geo_to_xyz(lon, lat, hoehe)


    # Die Kamera wird hier absichtlich NICHT angefasst.
    # Sie gehört dem Nutzer: Was er mit der Maus eingestellt hat,
    # bleibt so lange stehen, bis er es selbst ändert.


    # Flugbahn (gespeicherte Punkte + aktuelle Position)

    bahn_x = [round(punkt[0], 1) for punkt in flugbahn]
    bahn_y = [round(punkt[1], 1) for punkt in flugbahn]
    bahn_z = [round(punkt[2], 1) for punkt in flugbahn]

    bahn_x.append(round(x, 1))
    bahn_y.append(round(y, 1))
    bahn_z.append(round(z, 1))


    # Die Bahn wird in zwei Stücke geteilt:
    # das ältere (dünn) und das letzte Stück (hell und dick).
    # Sie dürfen sich nicht überlappen, sonst überdecken sich die
    # beiden Linien gegenseitig.
    ab = max(0, len(bahn_x) - HELLE_BAHN_PUNKTE)


    fig.data[TEIL_BAHN].x = bahn_x[:ab + 1]
    fig.data[TEIL_BAHN].y = bahn_y[:ab + 1]
    fig.data[TEIL_BAHN].z = bahn_z[:ab + 1]


    fig.data[TEIL_BAHN_NEU].x = bahn_x[ab:]
    fig.data[TEIL_BAHN_NEU].y = bahn_y[ab:]
    fig.data[TEIL_BAHN_NEU].z = bahn_z[ab:]


    # Lot zur Erdoberfläche
    # (ein kleines Stück über der Oberfläche, sonst verschwindet
    #  der Punkt in der Erdkugel)

    oben = lokale_achsen((x, y, z))[0]

    boden_hoehe = ERDRADIUS * 1.003

    boden_x = boden_hoehe * oben[0]
    boden_y = boden_hoehe * oben[1]
    boden_z = boden_hoehe * oben[2]


    fig.data[TEIL_LOT].x = [boden_x, x]
    fig.data[TEIL_LOT].y = [boden_y, y]
    fig.data[TEIL_LOT].z = [boden_z, z]


    fig.data[TEIL_BODENPUNKT].x = [boden_x]
    fig.data[TEIL_BODENPUNKT].y = [boden_y]
    fig.data[TEIL_BODENPUNKT].z = [boden_z]


    # Satellit

    fig.data[TEIL_RING].x = [x]
    fig.data[TEIL_RING].y = [y]
    fig.data[TEIL_RING].z = [z]


    # Beschriftung ein Stück über dem Satelliten, damit sie nicht
    # mitten im Ring steht
    fig.data[TEIL_BESCHRIFTUNG].x = [x + BESCHRIFTUNG_ABSTAND * oben[0]]
    fig.data[TEIL_BESCHRIFTUNG].y = [y + BESCHRIFTUNG_ABSTAND * oben[1]]
    fig.data[TEIL_BESCHRIFTUNG].z = [z + BESCHRIFTUNG_ABSTAND * oben[2]]


    fig.data[TEIL_MARKER].x = [x]
    fig.data[TEIL_MARKER].y = [y]
    fig.data[TEIL_MARKER].z = [z]

    fig.data[TEIL_MARKER].customdata = [
        [lon, lat, hoehe]
    ]


    koerper, panel_links, panel_rechts = satelliten_teile(
        (x, y, z)
    )


    for teil, punkte in (
        (TEIL_KOERPER, koerper),
        (TEIL_PANEL_LINKS, panel_links),
        (TEIL_PANEL_RECHTS, panel_rechts)
    ):

        fig.data[teil].x = punkte[0]
        fig.data[teil].y = punkte[1]
        fig.data[teil].z = punkte[2]


    return fig





# --------------------------------------------------
# Daten Funktionen
# --------------------------------------------------

def zeitreihe(
    eintraege,
    feld,
    beschriftung
):

    df = pd.DataFrame({

        "Zeit":
            pd.to_datetime(
                [
                    e["timestamp"]
                    for e in eintraege
                ],

                format="ISO8601"
            ),


        beschriftung:
            [
                e.get(feld)
                for e in eintraege
            ]
    })


    return (
        df
        .sort_values("Zeit")
        .set_index("Zeit")
    )





def aktueller_wert(
    eintraege,
    feld
):

    if not eintraege:
        return None


    neuester = max(

        eintraege,

        key=lambda e:
        pd.to_datetime(
            e["timestamp"],
            format="ISO8601"
        )
    )


    wert = neuester.get(feld)


    return (
        round(wert, 2)
        if wert is not None
        else None
    )



def abstand(punkt_a, punkt_b):
    """
    Abstand zwischen zwei 3D Punkten in km.
    """

    return math.sqrt(
        (punkt_a[0] - punkt_b[0]) ** 2 +
        (punkt_a[1] - punkt_b[1]) ** 2 +
        (punkt_a[2] - punkt_b[2]) ** 2
    )



def neueste_eintraege(eintraege, anzahl=MAX_ZEILEN_PRO_SENSOR):
    """
    Liefert die jüngsten Datensätze einer Komponente, neuester zuerst.

    Kommt ein neuer Datensatz dazu, fällt damit automatisch der
    älteste raus.
    """

    sortiert = sorted(
        eintraege,

        key=lambda e: pd.to_datetime(
            e["timestamp"],
            format="ISO8601"
        ),

        reverse=True
    )

    return sortiert[:anzahl]



def gerundet(eintrag, feld):
    """
    Liest einen Messwert aus einem Datensatz und rundet ihn.
    """

    wert = eintrag.get(feld)

    return (
        round(wert, 2)
        if wert is not None
        else None
    )



def tabelle_einfaerben(tabelle):
    """
    Färbt jede Zeile in der Farbe ihres Sensors und trennt die Blöcke.

    Arbeitet auf der ganzen Tabelle statt zeilenweise, weil für die
    Trennlinie bekannt sein muss, ob die Zeile darüber zum selben
    Sensor gehört.
    """

    stile = pd.DataFrame(
        "",
        index=tabelle.index,
        columns=tabelle.columns
    )

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
    """
    Sammelt die jüngsten Messwerte aller Komponenten für die Tabelle.
    """

    zeilen = []


    for schluessel, anzeigename in komponenten_namen.items():


        for eintrag in neueste_eintraege(
            daten.get(schluessel, [])
        ):

            zeile = {

                "Komponente":
                    anzeigename,

                "Zeit":
                    pd.to_datetime(
                        eintrag["timestamp"],
                        format="ISO8601"
                    )
            }


            for messgroesse in MESSGROESSEN:

                zeile[messgroesse["spalte"]] = gerundet(
                    eintrag,
                    messgroesse["feld"]
                )


            zeilen.append(zeile)


    return zeilen





# --------------------------------------------------
# Oberfläche
# --------------------------------------------------

def baue_oberflaeche():
    """
    Baut die Seite EINMAL auf und liefert die Platzhalter zurück.

    Vorher wurde bei jeder neuen Messung die ganze Seite neu erzeugt.
    Jetzt wird nur noch der Inhalt der Platzhalter ausgetauscht,
    dadurch flackert nichts mehr.
    """

    st.title(
        "Satellitendaten"
    )


    status_platzhalter = st.empty()


    # Tabelle + Rendering nebeneinander.
    # Die 3D Ansicht bekommt etwas mehr Platz, damit man bequem
    # darin herumdrehen kann.

    # Tabelle oben, darunter die 3D Ansicht.
    # Beide über die ganze Breite (keine Spalten mehr).

    st.subheader(
        f"Aktuelle Messwerte (letzte {MAX_ZEILEN_PRO_SENSOR} pro Sensor)"
    )

    tabellen_platzhalter = st.empty()


    st.subheader(
        "Umlaufbahn"
    )

    bahn_platzhalter = st.empty()


    # Nur ein Hinweistext, absichtlich kein Bedienelement:
    # Text löst keinen Neustart des Skripts aus.
    st.caption(
        "Ziehen = drehen · Mausrad = zoomen · "
        "Rechte Maustaste ziehen = verschieben · "
        "Doppelklick = Ansicht zurücksetzen"
    )


    # --------------------------------------------------
    # Live Diagramme
    # --------------------------------------------------

    st.subheader(
        "Live-Diagramme"
    )


    diagramm_platzhalter = []


    # Immer zwei Diagramme nebeneinander
    for start in range(0, len(diagramm_beschreibung), 2):

        spalten = st.columns(2)


        for spalte, beschreibung in zip(
            spalten,
            diagramm_beschreibung[start:start + 2]
        ):

            titel = beschreibung[2]


            with spalte, st.expander(
                titel,
                expanded=True
            ):

                diagramm_platzhalter.append(
                    st.empty()
                )


    return (
        status_platzhalter,
        tabellen_platzhalter,
        bahn_platzhalter,
        diagramm_platzhalter
    )



def zeige_tabelle(daten, tabellen_platzhalter):
    """
    Zeigt die letzten Messwerte pro Sensor als eingefärbte Tabelle.

    Die Tabelle wird immer in denselben Platzhalter gezeichnet.
    Dadurch wird sie nur ausgetauscht und die Seite flackert nicht.
    """

    zeilen = tabellen_zeilen_bauen(daten)


    if not zeilen:

        tabellen_platzhalter.info(
            "Noch keine Messwerte empfangen."
        )

        return


    tabelle = pd.DataFrame(zeilen).sort_values(
        ["Komponente", "Zeit"],
        ascending=[True, False]
    )


    stile = tabelle_einfaerben(tabelle)


    # Die Kopfzeile wird fett geschrieben. Bei der ersten und der
    # letzten Spalte kommt etwas Abstand zum Rand dazu.
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


    spalten_format = {
        fett["Zeit"]: lambda z: z.strftime("%Y-%m-%d %H:%M:%S")
    }

    for messgroesse in MESSGROESSEN:
        spalten_format[fett[messgroesse["spalte"]]] = "{:.2f}"


    tabellen_platzhalter.table(

        tabelle.style
            .apply(lambda _: stile, axis=None)

            # na_rep: Ohne das stürzt die Tabelle ab, sobald ein
            # Messwert fehlt.
            .format(
                spalten_format,
                na_rep=FEHLENDER_WERT
            )

            .set_table_styles(TABELLEN_STILE),

        border=False,

        hide_index=True,

        width="stretch"
    )



def zeige_messwerte(
    daten,
    tabellen_platzhalter,
    diagramm_platzhalter
):
    """
    Tabelle und Live-Diagramme neu füllen.
    """

    zeige_tabelle(
        daten,
        tabellen_platzhalter
    )


    for platzhalter, (
        schluessel,
        feld,
        titel,
        beschriftung
    ) in zip(
        diagramm_platzhalter,
        diagramm_beschreibung
    ):

        platzhalter.line_chart(

            zeitreihe(
                daten.get(schluessel, []),
                feld,
                beschriftung
            ),

            x_label="Zeit (Uhrzeit)",

            y_label=beschriftung
        )



# --------------------------------------------------
# Websocket
# --------------------------------------------------

async def stream_daten(platzhalter):

    (
        status_platzhalter,
        tabellen_platzhalter,
        bahn_platzhalter,
        diagramm_platzhalter
    ) = platzhalter


    uri = "ws://localhost:8000/ws"


    figur = erstelle_umlaufbahn()


    # Start- und Zielposition für die weiche Bewegung
    start_position = None
    ziel_position = None
    angezeigte_position = None
    gezeichnete_position = None

    letzte_aenderung = time.monotonic()
    uebergang_dauer = STANDARD_UEBERGANG

    bild_nummer = 0


    # --------------------------------------------------
    # Letzten Stand sofort wieder anzeigen
    # --------------------------------------------------

    # Startet das Skript neu (Verbindungsabbruch, Seite neu geladen),
    # dann sind alle Platzhalter leer. Ohne das Folgende wäre die
    # Seite erst einmal komplett leer - keine Tabelle, keine
    # Diagramme, keine Umlaufbahn.

    letzte_daten = st.session_state.get("letzte_daten")

    if letzte_daten:

        zeige_messwerte(
            letzte_daten,
            tabellen_platzhalter,
            diagramm_platzhalter
        )


    letzte_position = st.session_state.get("letzte_position")

    if letzte_position is not None:

        start_position = letzte_position
        angezeigte_position = letzte_position

        bild_nummer += 1


        bahn_platzhalter.plotly_chart(

            aktualisiere_umlaufbahn(
                figur,
                letzte_position,
                flugbahn_punkte,
                bild_nummer
            ),

            config=DIAGRAMM_BEDIENUNG
        )


    # close_timeout: Beim Beenden wird höchstens eine Sekunde auf den
    # Server gewartet. Sonst würde ein Neustart des Skripts sekundenlang
    # hängen bleiben.
    async with websockets.connect(
        uri,
        close_timeout=1
    ) as websocket:


        status_platzhalter.success(
            "Erfolgreich mit Satelliten-Datenstrom verbunden!"
        )


        # Das Empfangen läuft als eigene Aufgabe weiter.
        # So kann zwischendurch gezeichnet werden, auch wenn gerade
        # keine neuen Daten kommen.
        empfang = None


        while True:


            try:


                if empfang is None:

                    empfang = asyncio.create_task(
                        websocket.recv()
                    )


                fertig, _ = await asyncio.wait(
                    {empfang},
                    timeout=BILD_INTERVALL
                )


                # -------------------------
                # Neue Daten angekommen?
                # -------------------------

                if empfang in fertig:

                    daten_raw = empfang.result()

                    empfang = None


                    daten = json.loads(
                        daten_raw
                    )


                    # Merken, damit nach einem Neustart sofort wieder
                    # etwas zu sehen ist
                    st.session_state["letzte_daten"] = daten


                    zeige_messwerte(
                        daten,
                        tabellen_platzhalter,
                        diagramm_platzhalter
                    )


                    # -------------------------
                    # Position holen
                    # -------------------------

                    thruster_1 = daten.get(
                        "thruster_1.a",
                        []
                    )


                    lon = aktueller_wert(
                        thruster_1,
                        "x_deg"
                    )


                    lat = aktueller_wert(
                        thruster_1,
                        "y_deg"
                    )


                    hoehe = aktueller_wert(
                        thruster_1,
                        "z_km"
                    )


                    neue_position = (
                        (lon, lat, hoehe)

                        if None not in (lon, lat, hoehe)
                        else None
                    )


                    # Nur reagieren, wenn sich die Position wirklich
                    # geändert hat
                    if (
                        neue_position is not None and
                        neue_position != ziel_position
                    ):

                        jetzt = time.monotonic()


                        # So lange hat die letzte Messung gebraucht -
                        # genauso lange gleitet der Satellit jetzt.
                        uebergang_dauer = min(
                            max(
                                (jetzt - letzte_aenderung) *
                                UEBERGANG_ZUSCHLAG,

                                BILD_INTERVALL
                            ),
                            MAX_UEBERGANG
                        )


                        letzte_aenderung = jetzt

                        start_position = (
                            angezeigte_position or
                            neue_position
                        )

                        ziel_position = neue_position


                # -------------------------
                # Umlaufbahn zeichnen
                # -------------------------

                if ziel_position is not None:

                    anteil = min(
                        1.0,

                        (
                            time.monotonic() -
                            letzte_aenderung
                        ) / uebergang_dauer
                    )


                    angezeigte_position = zwischenposition(
                        start_position,
                        ziel_position,
                        anteil
                    )


                # Nur zeichnen, wenn der Satellit sich bewegt hat
                if (
                    angezeigte_position is not None and
                    angezeigte_position != gezeichnete_position
                ):

                    gezeichnete_position = angezeigte_position

                    bild_nummer += 1


                    # Merken, damit nach einem Neustart sofort wieder
                    # etwas zu sehen ist
                    st.session_state["letzte_position"] = (
                        angezeigte_position
                    )


                    punkt = geo_to_xyz(
                        *angezeigte_position
                    )


                    # Flugbahn erweitern (nicht bei jedem Bild, sonst
                    # werden es zu viele Punkte)
                    if (
                        not flugbahn_punkte or
                        abstand(
                            flugbahn_punkte[-1],
                            punkt
                        ) > MIN_BAHN_ABSTAND
                    ):

                        flugbahn_punkte.append(
                            punkt
                        )


                    # Es wird immer der gleiche Platzhalter benutzt.
                    # Dadurch wird das Diagramm nur aktualisiert und
                    # nicht jedes Mal komplett neu aufgebaut.
                    bahn_platzhalter.plotly_chart(

                        aktualisiere_umlaufbahn(
                            figur,
                            angezeigte_position,
                            flugbahn_punkte,
                            bild_nummer
                        ),


                        # Erlaubt Zoomen mit dem Mausrad und zeigt
                        # die Werkzeugleiste dauerhaft an.
                        config=DIAGRAMM_BEDIENUNG
                    )



            except websockets.exceptions.ConnectionClosed:


                if empfang is not None:
                    empfang.cancel()


                status_platzhalter.warning(
                    "Verbindung zum Server verloren. "
                    "Versuche erneuten Verbindungsaufbau..."
                )


                # Weiter nach oben geben. Dort wird die Verbindung
                # wirklich neu aufgebaut.
                raise





# --------------------------------------------------
# Start
# --------------------------------------------------

platzhalter = baue_oberflaeche()

status_platzhalter = platzhalter[0]


# Bricht die Verbindung ab oder läuft der Server noch nicht, wird
# hier einfach wieder von vorne probiert. Die Seite bleibt dabei
# stehen und zeigt weiter die letzten bekannten Werte an.
while True:

    try:

        asyncio.run(
            stream_daten(platzhalter)
        )


        # Hierher kommt man nur, wenn die Schleife von selbst endet.
        # Kurz warten, damit nicht ohne Pause neu verbunden wird.
        time.sleep(1)


    except (
        OSError,
        websockets.exceptions.WebSocketException
    ):

        status_platzhalter.warning(
            "Keine Verbindung zum Satelliten-Datenstrom. "
            "Läuft der Server? Neuer Versuch in 2 Sekunden ..."
        )


        time.sleep(2)
