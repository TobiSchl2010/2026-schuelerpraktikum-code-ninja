# Import 
import streamlit as st
import pandas as pd 
import asyncio
import websockets
import json

async def get_data():

    uri = "ws://localhost:8000/ws"

    async with websockets.connect(uri) as websocket:

        daten = await websocket.recv()

        return json.loads(daten)


daten = asyncio.run(get_data())


wasserstoff = daten["hydrogen_tank_1"]
sauerstoff = daten["oxygen_tank_1"]
thruster_1 = daten["thruster_1.a"]

zeit_o = [eintrag["timestamp"] for eintrag in sauerstoff]

temperatur_o = [
    eintrag["temperature"]
    for eintrag in sauerstoff
]

druck_o = [
    eintrag["pressure"]
    for eintrag in sauerstoff
]

zeit_h = [
    eintrag["timestamp"]
    for eintrag in wasserstoff
]

temperatur_h = [
    eintrag["temperature"]
    for eintrag in wasserstoff
]

druck_h = [
    eintrag["pressure"]
    for eintrag in wasserstoff
]

zeit_thruster_1 = [
    eintrag["timestamp"]
    for eintrag in thruster_1
]

temperatur_thruster_1 = [
    eintrag["temperature"]
    for eintrag in thruster_1
]

druck_thruster_1 = [
    eintrag["pressure"]
    for eintrag in thruster_1
]






#druckH1 = 2.9
#druckH2 = 1.5
#druckO1 = 1.0
#druckO2 = 5.8
#zeit1 = "2020-12-12 12:30"
#zeit2 = "2020-12-12 13:30"
#temperaturH1 = 30
#temperaturH2 = 50
#temperaturO1 = 10
#temperaturO2 = 40
#Entfernung1 = 2200000
#Entfernung2 = 500070


# Titel: große sauber formatierte Überschrift ganz oben auf der Seite 
st.title("Satelitendaten")



# Tabelle erstellen 
#tabelleO = pd.DataFrame ({
       #  "Sensorname": "Sauerstofftank",
       #  "Zeitstempel": [zeit[zeit]],
       # "Temperatur (in °C)": [temperaturO[temperaturO]],
       #  "Druck (in Bar)": [druckO[druckO]], 
         #"Entfernung zur Erde (in km)": [Entfernung2],
        #    })



#with st.expander("Letzte Daten vom Sauerstofftank"):
    # Tabelle anzeigen
    #st.dataframe(tabelleO)


# Diagramme 

st.subheader("Diagramme")

    
with st.expander("Temperatur vom Sauerstofftank"):
    daten = pd.DataFrame ({
    "Zeit": [zeit_o[i] for i in range(len(zeit_o))],
    "Druck": [temperatur_o[i] for i in range(len(temperatur_o))]
        })

    # Zeit als Index für die X-Achse
    daten = daten.set_index("Zeit")

    st.line_chart(daten)   

with st.expander("Druck vom Sauerstofftank"):
    daten = pd.DataFrame ({
    "Zeit": [zeit_o[i] for i in range(len(zeit_o))],
    "Druck": [druck_o[i] for i in range(len(druck_o))]
        })
    daten = daten.set_index("Zeit")
    st.line_chart(daten) 


with st.expander("Temperatur vom Wasserstofftank"):
    daten = pd.DataFrame ({
    "Zeit": [zeit_h[i] for i in range(len(zeit_h))],
    "Druck": [temperatur_h[i] for i in range(len(temperatur_h))]
        })

    # Zeit als Index für die X-Achse
    daten = daten.set_index("Zeit")

    st.line_chart(daten)


with st.expander("Druck vom Wasserstofftank"):
    daten = pd.DataFrame ({
    "Zeit": [zeit_h[i] for i in range(len(zeit_h))],
    "Druck": [druck_h[i] for i in range(len(druck_h))]
        })
    daten = daten.set_index("Zeit")
    st.line_chart(daten)

with st.expander("Temperatur vom Triebwerk 1.A"):
    daten = pd.DataFrame ({
    "Zeit": [zeit_thruster_1[i] for i in range(len(zeit_thruster_1))],
    "Druck": [temperatur_thruster_1[i] for i in range(len(temperatur_thruster_1))]
        })

    # Zeit als Index für die X-Achse
    daten = daten.set_index("Zeit")

    st.line_chart(daten)


with st.expander("Druck vom Triebwerk 1.A"):
    daten = pd.DataFrame ({
    "Zeit": [zeit_thruster_1[i] for i in range(len(zeit_thruster_1))],
    "Druck": [druck_thruster_1[i] for i in range(len(druck_thruster_1))]
        })

    # Zeit als Index für die X-Achse
    daten = daten.set_index("Zeit")

    st.line_chart(daten)




# with st.expander("Entfernung zur Erde"):
#     daten = pd.DataFrame({
#         "Zeit": [
#            zeit1,
#            zeit2
#            ],

#         "Entfernung": [
#             Entfernung2,
#             Entfernung1
#             ]
#         })

#     # Zeit als Index für die X-Achse
#     daten = daten.set_index("Zeit")
#     st.line_chart(daten)   