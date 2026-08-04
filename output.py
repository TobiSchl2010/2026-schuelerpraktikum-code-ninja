# Import 
import streamlit as st
import pandas as pd 


druckH1 = 2.9
druckH2 = 1.5
druckO1 = 1.0
druckO2 = 5.8
zeit1 = "2020-12-12 12:30"
zeit2 = "2020-12-12 13:30"
temperaturH1 = 30
temperaturH2 = 50
temperaturO1 = 10
temperaturO2 = 40
Entfernung1 = 2200000
Entfernung2 = 500070


# Titel: große sauber formatierte Überschrift ganz oben auf der Seite 
st.title("Satelitendaten")



# Tabelle erstellen 
tabelle = pd.DataFrame ({
         "Sensorname": ["sensor1"],
         "Zeitstempel": [zeit1],
         "Temperatur (in °C)": [temperaturO2],
         "Druck (in Bar)": [druckO2],
         #"Entfernung zur Erde (in km)": [Entfernung2],
            })



with st.expander("Letzte Daten"):
    # Tabelle anzeigen
    st.dataframe(tabelle)


# Diagramme 

st.subheader("Diagramme")



with st.expander("Druck vom Sauerstofftank"):
    daten = pd.DataFrame ({
            "Zeit": [
                zeit1,
                zeit2
            ],

            "Druck": [
                druckO1,
                druckO2
            ]
        })
    daten = daten.set_index("Zeit")
    st.line_chart(daten)


with st.expander("Druck vom Wasserstofftank"):
    daten = pd.DataFrame ({
        "Zeit": [
            zeit1,
            zeit2
        ],
        
         "Druck": [
             druckH1, 
             druckH2
               ]
                })
    daten = daten.set_index("Zeit")
    st.line_chart(daten)
    
    


with st.expander("Temperatur vom Wasserstofftank"):
    daten = pd.DataFrame({
    "Zeit": [
        zeit1,
        zeit2
    ],
    "Temperatur": [
        temperaturH1,
        temperaturH2
    ]
    })

    # Zeit als Index für die X-Achse
    daten = daten.set_index("Zeit")

    st.line_chart(daten)


with st.expander("Temperatur vom Sauerstofftank"):
   daten = pd.DataFrame({
       "Zeit": [
           zeit1,
           zeit2
           ],

           "Temperatur": [
               temperaturO1,
               temperaturO2
               ]
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