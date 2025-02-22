import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import openai
from streamlit_chat import message
import json
from geopy.geocoders import Nominatim
import os
from dotenv import load_dotenv

load_dotenv()

# Najpierw spróbuj załadować z .env, jeśli nie ma, użyj secrets ze Streamlit
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY") or st.secrets["api_keys"]["GOOGLE_MAPS_API_KEY"]
openai.api_key = os.getenv("OPENAI_API_KEY") or st.secrets["api_keys"]["OPENAI_API_KEY"]

# Inicjalizacja stanu sesji
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Witaj! Jestem Twoim asystentem podróży i ekspertem od lokalizacji w Europie. Pomogę Ci w:\n\n"
         "🗺️ Analizie lokalizacji:\n"
         "- Szczegółowe informacje o wybranych miejscach\n"
         "- Pobliskie atrakcje i ukryte perełki\n"
         "- Lokalne zwyczaje i kultura\n\n"
         "🚗 Planowaniu podróży:\n"
         "- Optymalne trasy między lokalizacjami\n"
         "- Różne opcje transportu (komunikacja miejska, samochód, rower)\n"
         "- Szacowany czas i koszty podróży\n\n"
         "💡 Praktycznych poradach:\n"
         "- Najlepszy czas na zwiedzanie\n"
         "- Informacje o parkingach i komunikacji\n"
         "- Lokalne wydarzenia i festiwale\n\n"
         "Wybierz do 5 lokalizacji z tabeli po prawej stronie, a pomogę Ci zaplanować najlepszą trasę i dostarczę przydatnych informacji. W czym mogę Ci pomóc?"}
    ]
if 'selected_coordinates' not in st.session_state:
    st.session_state.selected_coordinates = []
if 'selected_count' not in st.session_state:
    st.session_state.selected_count = 0

# Funkcja do wczytywania danych
@st.cache_data
def load_data():
    df = pd.read_csv("locations.csv", sep=';')
    return df

# Funkcja do generowania odpowiedzi z ChatGPT
def get_chatgpt_response(prompt, selected_coordinates) -> str:
    context = f"Selected locations coordinates: {selected_coordinates}\n\n"
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": """You are an experienced travel and location analysis assistant specializing in European destinations. Your tasks include:

1. Location Analysis:
- Analyze selected locations and their surroundings
- Provide detailed information about points of interest
- Suggest nearby attractions and hidden gems
- Compare different locations in terms of tourist appeal
- Inform about local climate and best times to visit

2. Travel Planning:
- Recommend optimal routes between selected locations
- Suggest transportation options (public transport, car, bike, walking)
- Estimate travel times and costs
- Provide tips for the most efficient and scenic routes
- Alert about potential travel disruptions or challenges

3. Local Knowledge:
- Share insights about local culture and customs
- Recommend local cuisine and restaurants
- Provide information about accommodation options
- Alert about safety considerations
- Mention language considerations and useful phrases

4. Practical Advice:
- Suggest best times for visiting specific locations
- Provide parking information when relevant
- Mention accessibility considerations
- Give tips about local events and festivals
- Share practical tips about local transportation systems

When multiple locations are selected, focus on:
- Finding logical routes between them
- Suggesting optimal visit order
- Estimating total journey time
- Providing multi-stop itinerary suggestions
- Highlighting potential connections and relationships between locations

Communicate in a friendly, conversational tone and always prioritize practical, actionable advice."""},
                {"role": "user", "content": context + prompt}
            ]
        )
        if response and response.choices and response.choices[0].message:
            return str(response.choices[0].message.content)
        return "Przepraszam, nie udało się wygenerować odpowiedzi."
    except Exception as e:
        return f"Error: {str(e)}"

# Ustawienie strony
st.set_page_config(layout="wide")
st.title("Location Explorer with Chat")

# Wczytanie danych
df = load_data()

# Tworzenie layoutu z kolumnami
col1, col2 = st.columns([1, 1])

with col1:
    # Chat interface
    st.subheader("Chat")
    
    # Wyświetlenie historii czatu
    chat_container = st.container()
    with chat_container:
        for idx, msg in enumerate(st.session_state.messages):
            message(msg["content"], 
                   is_user=msg["role"] == "user", 
                   key=f"msg_{idx}")
    
    # Input dla wiadomości
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""
    
    user_input = st.text_input("Your message:", key="input_field", value=st.session_state.user_input)
    
    if st.button("Send"):
        if user_input:
            # Zapisz wiadomość użytkownika
            st.session_state.messages.append({"role": "user", "content": user_input})
            # Generuj odpowiedź
            response = get_chatgpt_response(user_input, st.session_state.selected_coordinates)
            if response:
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                st.session_state.messages.append({"role": "assistant", "content": "Przepraszam, wystąpił błąd podczas generowania odpowiedzi."})
            # Wyczyść pole input
            st.session_state.user_input = ""
            # Odśwież stronę
            st.rerun()

with col2:
    # Tabela z checkboxami
    st.subheader("Locations Table")
    
    # Tworzenie dataframe dla wyświetlenia
    display_df = df.copy()
    display_df['Select'] = False
    
    # Konwertowanie dataframe na HTML z checkboxami
    st.write("Wybierz maksymalnie 5 lokalizacji:")
    
    # Tworzenie tabeli z checkboxami
    selected_indices = []
    for index, row in df.iterrows():
        col1, col2 = st.columns([0.1, 0.9])
        with col1:
            # Sprawdzanie limitu zaznaczonych lokalizacji
            is_disabled = st.session_state.selected_count >= 5 and f"checkbox_{index}" not in st.session_state
            checkbox = st.checkbox('', key=f"checkbox_{index}", disabled=is_disabled)
            if checkbox:
                selected_indices.append(index)
                if f"checkbox_{index}" not in st.session_state:
                    st.session_state.selected_count += 1
            elif f"checkbox_{index}" in st.session_state and not checkbox:
                st.session_state.selected_count -= 1
        with col2:
            st.write(f"{row['address']}")
    
    # Wyświetlenie licznika wybranych lokalizacji
    st.write(f"Wybrano {st.session_state.selected_count}/5 lokalizacji")
    
    # Filtrowanie wybranych lokalizacji
    selected_rows = df.iloc[selected_indices]
    
    if not selected_rows.empty:
        st.write("Selected Locations:")
        st.dataframe(selected_rows[['address', 'latitude', 'longitude']])
        st.session_state.selected_coordinates = selected_rows[['latitude', 'longitude']].values.tolist()

# Mapa na dole
st.subheader("Map")
map_container = st.container()
with map_container:
    m = folium.Map(location=[50.0, 19.0], zoom_start=4)
    
    # Dodawanie markerów
    for idx, row in df.iterrows():
        folium.Marker(
            [row['latitude'], row['longitude']],
            popup=row['address'],
            icon=folium.Icon(color='red' if idx in selected_indices else 'blue')
        ).add_to(m)
    
    folium_static(m)