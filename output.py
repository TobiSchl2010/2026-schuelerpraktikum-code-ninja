# Import 
import streamlit as st
import pandas as pd 

druckH = [1.5, 3.5]
druckO = [2.5, 5.0]
zeit = ["2020-12-12 12:30", "2020-12-12 13:30"]
temperaturH = [14.00, 20.15]
temperaturO = [90.00, 95.00]
entfernung = [160, 2000]
komponente = ["Wasserstofftank", "Sauerstofftank"]


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
tabelleO = pd.DataFrame ({
         "Sensorname": "Sauerstofftank",
         "Zeitstempel": [zeit[zeit]],
         "Temperatur (in °C)": [temperaturO[temperaturO]],
         "Druck (in Bar)": [druckO[druckO]],
         "Entfernung zur Erde (in km)": [entfernung[entfernung]]
            })



with st.expander("Letzte Daten vom Sauerstofftank"):
    # Tabelle anzeigen
    st.dataframe(tabelleO)


# Diagramme 

st.subheader("Diagramme")



with st.expander("Druck vom Sauerstofftank"):
    daten = pd.DataFrame ({
    "Zeit": [zeit[i] for i in range(len(zeit))],
    "Druck": [druckO[i] for i in range(len(druckO))]
        })
    daten = daten.set_index("Zeit")
    st.line_chart(daten)


with st.expander("Druck vom Wasserstofftank"):
    daten = pd.DataFrame ({
    "Zeit": [zeit[i] for i in range(len(zeit))],
    "Druck": [druckH[i] for i in range(len(druckH))]
        })
    daten = daten.set_index("Zeit")
    st.line_chart(daten)
    
    


with st.expander("Temperatur vom Wasserstofftank"):
    daten = pd.DataFrame ({
    "Zeit": [zeit[i] for i in range(len(zeit))],
    "Druck": [temperaturH[i] for i in range(len(temperaturH))]
        })

    # Zeit als Index für die X-Achse
    daten = daten.set_index("Zeit")

    st.line_chart(daten)


with st.expander("Temperatur vom Sauerstofftank"):
    daten = pd.DataFrame ({
    "Zeit": [zeit[i] for i in range(len(zeit))],
    "Druck": [temperaturO[i] for i in range(len(temperaturO))]
        })

    # Zeit als Index für die X-Achse
    daten = daten.set_index("Zeit")

    st.line_chart(daten)


with st.expander("Entfernung zur Erde"):
    daten = pd.DataFrame({
        "Zeit": 
        [zeit [i] for i in range(len(zeit))],
        "Entfernung":
        [entfernung [i] for i in range(len(entfernung))],
        })

#     # Zeit als Index für die X-Achse
#     daten = daten.set_index("Zeit")
#     st.line_chart(daten)   