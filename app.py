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
        {"role": "assistant", "content": "Witaj! Jestem asystentem do analizy tras handlowych. Pomogę Ci w:\n\n"
         "📊 Analizie klientów:\n"
         "- Szczegółowe informacje o punktach handlowych\n"
         "- Historia zamówień i przychody\n"
         "- Priorytety i preferowane godziny kontaktu\n\n"
         "🚗 Planowaniu tras:\n"
         "- Optymalne trasy między punktami\n"
         "- Szacowany czas przejazdu\n"
         "- Sugestie kolejności wizyt\n\n"
         "💡 Analizie biznesowej:\n"
         "- Priorytety klientów\n"
         "- Potencjał sprzedażowy\n"
         "- Rekomendacje działań\n\n"
         "Wybierz punkty na mapie (maksymalnie 5 lokalizacji), a pomogę Ci zaplanować optymalną trasę i dostarczę przydatnych informacji biznesowych. W czym mogę Ci pomóc?"}
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
                {"role": "system", "content": """You are an experienced sales route and business analysis assistant. Your tasks include:

1. Client Analysis:
- Analyze client types and their business potential
- Review purchase history and revenue data
- Assess client priorities and contact preferences
- Provide insights about client's business profile
- Suggest potential upselling opportunities

2. Route Planning:
- Recommend optimal routes between selected locations
- Consider client priority levels when planning
- Estimate travel times and distances
- Suggest best visit order based on client preferences
- Account for preferred contact hours

3. Business Intelligence:
- Analyze revenue patterns
- Identify high-priority clients
- Suggest sales opportunities
- Provide competitive insights
- Recommend business development strategies

4. Practical Advice:
- Suggest best times for client visits
- Note any specific client requirements
- Provide tips for efficient meetings
- Calculate potential route revenues
- Highlight key business opportunities

When multiple locations are selected, focus on:
- Optimizing route efficiency
- Prioritizing high-value clients
- Maximizing sales potential
- Creating time-efficient schedules
- Considering preferred contact hours

Communicate in a professional, business-focused tone and prioritize actionable insights that can increase sales effectiveness."""},
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