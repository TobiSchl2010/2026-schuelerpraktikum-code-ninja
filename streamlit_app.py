# Import
import asyncio
import json
import math
import random

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import websockets
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Satellitendaten", layout="wide")

# Anzeigenamen der Komponenten fuer die Tabelle
komponenten_namen = {
    "oxygen_tank_1": "Sauerstofftank",
    "hydrogen_tank_1": "Wasserstofftank",
    "thruster_1.a": "Triebwerk 1.A"
}

# Bahnpunkte des Satelliten (feste Beispieldaten)
bahn_x = [
    6921, 6802, 6454, 5901, 5191,
    4343, 3380, 2328, 1214, 0,
    -1214, -2328, -3380, -4343, -5191,
    -5901, -6454, -6802, -6921, -6802,
    -6454, -5901, -5191, -4343, -3380,
    -2328, -1214, 0, 1214, 2328,
    3380, 4343, 5191, 5901, 6454,
    6802, 6921
]

bahn_y = [
    0, 1214, 2328, 3380, 4343,
    5191, 5901, 6454, 6802, 6921,
    6802, 6454, 5901, 5191, 4343,
    3380, 2328, 1214, 0, -1214,
    -2328, -3380, -4343, -5191, -5901,
    -6454, -6802, -6921, -6802, -6454,
    -5901, -5191, -4343, -3380, -2328,
    -1214, 0
]

bahn_z = [
    0, 200, 390, 560, 710,
    830, 920, 980, 1010, 1020,
    1010, 980, 920, 830, 710,
    560, 390, 200, 0, -200,
    -390, -560, -710, -830, -920,
    -980, -1010, -1020, -1010, -980,
    -920, -830, -710, -560, -390,
    -200, 0
]


def sterne(anzahl=1200, radius=18000, freier_bereich=9000):
    """Verteilt Sterne im ganzen Raum rund um die Bahn, nicht nur auf einer Kugelschale."""
    # Fester Startwert: die Sterne stehen bei jedem Neuladen an derselben Stelle
    zufall = random.Random(42)

    x, y, z, groessen = [], [], [], []
    while len(x) < anzahl:
        # Zufaelliger Punkt irgendwo im Wuerfel rund um die Bahn
        px = zufall.uniform(-radius, radius)
        py = zufall.uniform(-radius, radius)
        pz = zufall.uniform(-radius, radius)

        # Direkt um die Bahn herum bleibt es frei, sonst liegen Sterne auf der Flugbahn
        if math.sqrt(px ** 2 + py ** 2 + pz ** 2) < freier_bereich:
            continue

        x.append(px)
        y.append(py)
        z.append(pz)
        # Unterschiedliche Groessen lassen die Sterne raeumlich wirken
        groessen.append(zufall.choice([1, 1, 1, 1.5, 2, 3]))

    return x, y, z, groessen


def erde(radius=6371, aufloesung=48):
    """Kugel im Mittelpunkt der Bahn - der Satellit kreist um sie herum."""
    laengengrade = [2 * math.pi * i / aufloesung for i in range(aufloesung + 1)]
    breitengrade = [math.pi * j / aufloesung for j in range(aufloesung + 1)]

    # Kugelkoordinaten in x/y/z umrechnen, jede Zeile ist ein Breitengrad
    x = [[radius * math.sin(b) * math.cos(l) for l in laengengrade] for b in breitengrade]
    y = [[radius * math.sin(b) * math.sin(l) for l in laengengrade] for b in breitengrade]
    z = [[radius * math.cos(b) for _ in laengengrade] for b in breitengrade]

    return go.Surface(
        x=x,
        y=y,
        z=z,
        # Pole dunkler, Aequator heller - das laesst die Kugel plastisch wirken
        colorscale=[[0, "#0a2a5e"], [0.5, "#1565C0"], [1, "#0a2a5e"]],
        showscale=False,
        hoverinfo="skip",
        name="Erde",
        lighting=dict(ambient=0.4, diffuse=0.9, specular=0.1),
        lightposition=dict(x=30000, y=30000, z=15000)
    )


def quader(mittelpunkt, halbe_kanten, farbe, name, in_legende=False):
    """Baut einen Quader aus seinen acht Ecken (alphahull=0 verbindet sie zur Huelle)."""
    mx, my, mz = mittelpunkt
    hx, hy, hz = halbe_kanten

    x, y, z = [], [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                x.append(mx + sx * hx)
                y.append(my + sy * hy)
                z.append(mz + sz * hz)

    return go.Mesh3d(
        x=x,
        y=y,
        z=z,
        alphahull=0,
        color=farbe,
        flatshading=True,
        hoverinfo="skip",
        name=name,
        showlegend=in_legende
    )


def satellit(position, groesse=700):
    """Kleiner Satellit aus Koerper und zwei Solarpanelen (nicht massstabsgetreu)."""
    mx, my, mz = position

    koerper = quader(
        (mx, my, mz),
        (groesse * 0.25, groesse * 0.25, groesse * 0.25),
        "#E0E0E0",
        "Satellit",
        in_legende=True
    )

    # Die beiden Panele haengen links und rechts am Koerper
    panel_links = quader(
        (mx, my - groesse * 0.7, mz),
        (groesse * 0.18, groesse * 0.45, groesse * 0.03),
        "#1565C0",
        "Solarpanel"
    )
    panel_rechts = quader(
        (mx, my + groesse * 0.7, mz),
        (groesse * 0.18, groesse * 0.45, groesse * 0.03),
        "#1565C0",
        "Solarpanel"
    )

    return [koerper, panel_links, panel_rechts]


def umlaufbahn():
    """Baut die 3D-Ansicht der Flugbahn mit der aktuellen Satellitenposition."""
    fig = go.Figure()

    # Skybox: Sternenhimmel als Hintergrund
    stern_x, stern_y, stern_z, stern_groessen = sterne()
    fig.add_trace(go.Scatter3d(
        x=stern_x,
        y=stern_y,
        z=stern_z,
        mode="markers",
        marker=dict(size=stern_groessen, color="white", opacity=0.9),
        hoverinfo="skip",
        showlegend=False
    ))

    # Erde im Mittelpunkt der Umlaufbahn
    fig.add_trace(erde())

    # Flugbahn
    fig.add_trace(go.Scatter3d(
        x=bahn_x,
        y=bahn_y,
        z=bahn_z,
        mode="lines",
        line=dict(color="#4FC3F7", width=4),
        name="Bahn"
    ))

    # Aktuelle Position: Satellit am letzten Bahnpunkt
    for teil in satellit((bahn_x[-1], bahn_y[-1], bahn_z[-1])):
        fig.add_trace(teil)

    # Achsen komplett ausblenden - im Weltraum gibt es kein Gitternetz
    achse_unsichtbar = dict(
        visible=False,
        showgrid=False,
        zeroline=False,
        showbackground=False,
        showticklabels=False,
        title=""
    )

    fig.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="black",
        font=dict(color="white"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        scene=dict(
            bgcolor="black",
            # aspectmode="data" haelt die Achsen im echten Groessenverhaeltnis
            aspectmode="data",
            xaxis=achse_unsichtbar,
            yaxis=achse_unsichtbar,
            zaxis=achse_unsichtbar,
            camera=dict(eye=dict(x=1.0, y=1.0, z=0.55))
        )
    )
    return fig


def zeitreihe(eintraege, feld, beschriftung):
    """Baut aus den Rohdaten einen DataFrame mit lesbarer Zeitachse."""
    df = pd.DataFrame({
        "Zeit": pd.to_datetime([e["timestamp"] for e in eintraege], format="ISO8601"),
        beschriftung: [e.get(feld) for e in eintraege]
    })
    # Aelteste Werte zuerst, damit das Diagramm von links nach rechts laeuft
    return df.sort_values("Zeit").set_index("Zeit")


def aktueller_wert(eintraege, feld):
    """Liefert den neuesten Messwert einer Komponente."""
    if not eintraege:
        return None
    neuester = max(eintraege, key=lambda e: pd.to_datetime(e["timestamp"], format="ISO8601"))
    wert = neuester.get(feld)
    return round(wert, 2) if wert is not None else None


# --- Grundgeruest der Seite ---
# Wird einmal aufgebaut, die Live-Daten fuellen spaeter nur noch die Platzhalter.
st.title("Satellitendaten")
status_platzhalter = st.empty()

# Kopfbereich: links die aktuellen Messwerte, rechts die Umlaufbahn
spalte_werte, spalte_bahn = st.columns(2)

with spalte_werte:
    st.subheader("Aktuelle Messwerte")
    tabellen_platzhalter = st.empty()

with spalte_bahn:
    st.subheader("Umlaufbahn")
    # Die Bahn ist fest, sie wird nur einmal gezeichnet und flackert dadurch nicht.
    st.plotly_chart(umlaufbahn(), use_container_width=True)

st.subheader("Live-Diagramme")
diagramm_platzhalter = st.empty()


async def stream_daten():

    uri = "ws://localhost:8000/ws"

    async with websockets.connect(uri) as websocket:

        status_platzhalter.success("Erfolgreich mit Satelliten-Datenstrom verbunden!")

        # Endlosschleife: Solange die Verbindung steht, lauschen wir auf Daten
        while True:
            try:
                daten_raw = await websocket.recv()

                daten = json.loads(daten_raw)

                wasserstoff = daten.get("hydrogen_tank_1", [])
                sauerstoff = daten.get("oxygen_tank_1", [])
                thruster_1 = daten.get("thruster_1.a", [])

                # --- Tabelle ---
                tabellen_zeilen = []
                for schluessel, anzeigename in komponenten_namen.items():
                    eintraege = daten.get(schluessel, [])
                    tabellen_zeilen.append({
                        "Komponente": anzeigename,
                        "Temperatur (K)": aktueller_wert(eintraege, "temperature"),
                        "Druck (bar)": aktueller_wert(eintraege, "pressure")
                    })

                tabellen_platzhalter.dataframe(
                    pd.DataFrame(tabellen_zeilen),
                    hide_index=True,
                    use_container_width=True
                )
                # ----------------

                with diagramm_platzhalter.container():

                    # --- SAUERSTOFF ---
                    col1, col2 = st.columns(2)

                    # Hier sind Spalte und Expander in einer Zeile kombiniert:
                    with col1, st.expander("Temperatur vom Sauerstofftank", expanded=True):
                        df_o_temp = zeitreihe(sauerstoff, "temperature", "Temperatur (K)")
                        st.line_chart(
                            df_o_temp,
                            x_label="Zeit (Uhrzeit)",
                            y_label="Temperatur (K)"
                        )

                    with col2, st.expander("Druck vom Sauerstofftank", expanded=True):
                        df_o_druck = zeitreihe(sauerstoff, "pressure", "Druck (bar)")
                        st.line_chart(
                            df_o_druck,
                            x_label="Zeit (Uhrzeit)",
                            y_label="Druck (bar)"
                        )

                    # --- WASSERSTOFF ---
                    col3, col4 = st.columns(2)

                    with col3, st.expander("Temperatur vom Wasserstofftank", expanded=True):
                        df_h_temp = zeitreihe(wasserstoff, "temperature", "Temperatur (K)")
                        st.line_chart(
                            df_h_temp,
                            x_label="Zeit (Uhrzeit)",
                            y_label="Temperatur (K)"
                        )

                    with col4, st.expander("Druck vom Wasserstofftank", expanded=True):
                        df_h_druck = zeitreihe(wasserstoff, "pressure", "Druck (bar)")
                        st.line_chart(
                            df_h_druck,
                            x_label="Zeit (Uhrzeit)",
                            y_label="Druck (bar)"
                        )

                    # --- TRIEBWERK ---
                    col5, col6 = st.columns(2)

                    with col5, st.expander("Temperatur vom Triebwerk 1.A", expanded=True):
                        df_t_temp = zeitreihe(thruster_1, "temperature", "Temperatur (K)")
                        st.line_chart(
                            df_t_temp,
                            x_label="Zeit (Uhrzeit)",
                            y_label="Temperatur (K)"
                        )

                    with col6, st.expander("Druck vom Triebwerk 1.A", expanded=True):
                        df_t_druck = zeitreihe(thruster_1, "pressure", "Druck (bar)")
                        st.line_chart(
                            df_t_druck,
                            x_label="Zeit (Uhrzeit)",
                            y_label="Druck (bar)"
                        )

            except websockets.exceptions.ConnectionClosed:
                status_platzhalter.error("Verbindung zum Server verloren. Versuche erneuten Verbindungsaufbau...")
                await asyncio.sleep(2)
                break


daten = asyncio.run(stream_daten())
