import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import openai
from streamlit_chat import message
import json
from geopy.geocoders import Nominatim

# Konfiguracja API keys - odczytywanie z secrets Streamlit
GOOGLE_MAPS_API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
openai.api_key = st.secrets["OPENAI_API_KEY"]

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
         "Kliknij na mapie (maksymalnie 5 lokalizacji), a pomogę Ci zaplanować najlepszą trasę i dostarczę przydatnych informacji. W czym mogę Ci pomóc?"}
    ]
if 'selected_locations' not in st.session_state:
    st.session_state.selected_locations = []

# Funkcja do wczytywania danych
@st.cache_data
def load_data():
    df = pd.read_csv("locations.csv", sep=';')
    return df

# Funkcja do generowania odpowiedzi z ChatGPT
def get_chatgpt_response(prompt, selected_locations) -> str:
    locations_info = []
    for loc in selected_locations:
        locations_info.append(f"{loc['address']} (lat: {loc['lat']}, lon: {loc['lon']})")
    
    context = f"Selected locations: {', '.join(locations_info)}\n\n"
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
            response = get_chatgpt_response(user_input, st.session_state.selected_locations)
            if response:
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                st.session_state.messages.append({"role": "assistant", "content": "Przepraszam, wystąpił błąd podczas generowania odpowiedzi."})
            # Wyczyść pole input
            st.session_state.user_input = ""
            # Odśwież stronę
            st.rerun()

with col2:
    # Wyświetlenie wybranych lokalizacji z przyciskami do usuwania
    st.write(f"Wybrano {len(st.session_state.selected_locations)}/5 lokalizacji:")
    
    # Tworzymy nową listę do przechowywania lokalizacji po usunięciach
    locations_to_keep = st.session_state.selected_locations.copy()
    
    for i, loc in enumerate(st.session_state.selected_locations):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"📍 {loc['address']}")
        with col2:
            if st.button("Usuń", key=f"remove_{i}"):
                locations_to_keep.remove(loc)
                st.session_state.selected_locations = locations_to_keep
                st.rerun()

    # Mapa z możliwością zaznaczania
    st.subheader("Interactive Map")
    
    # Tworzenie mapy
    m = folium.Map(location=[50.0, 19.0], zoom_start=4)
    
    # Dodawanie markerów
    for idx, row in df.iterrows():
        location = [row['latitude'], row['longitude']]
        is_selected = any(loc['lat'] == location[0] and loc['lon'] == location[1] 
                         for loc in st.session_state.selected_locations)
        
        folium.Marker(
            location,
            popup=row['address'],
            icon=folium.Icon(color='red' if is_selected else 'blue'),
        ).add_to(m)
    
    # Wyświetlenie mapy z możliwością interakcji
    map_data = st_folium(m, width=800, height=500, key="map")
    
    # Obsługa kliknięć na mapie
    if map_data is not None and 'last_object_clicked' in map_data:
        clicked = map_data['last_object_clicked']
        if clicked is not None:
            lat, lon = clicked['lat'], clicked['lng']
            # Sprawdź czy kliknięto w marker
            clicked_location = df[
                (df['latitude'].round(6) == round(lat, 6)) & 
                (df['longitude'].round(6) == round(lon, 6))
            ]
            
            if not clicked_location.empty:
                loc_data = clicked_location.iloc[0]
                # Sprawdź czy lokalizacja jest już wybrana
                is_selected = any(
                    loc['lat'] == loc_data['latitude'] and 
                    loc['lon'] == loc_data['longitude'] 
                    for loc in st.session_state.selected_locations
                )
                
                if not is_selected and len(st.session_state.selected_locations) < 5:
                    # Dodaj lokalizację
                    st.session_state.selected_locations.append({
                        'address': loc_data['address'],
                        'lat': loc_data['latitude'],
                        'lon': loc_data['longitude']
                    })
                    st.rerun()
                elif is_selected:
                    # Usuń lokalizację
                    st.session_state.selected_locations = [
                        loc for loc in st.session_state.selected_locations 
                        if not (loc['lat'] == loc_data['latitude'] and 
                               loc['lon'] == loc_data['longitude'])
                    ]
                    st.rerun()