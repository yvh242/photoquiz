import streamlit as st
import PIL.Image as Image
import numpy as np
import time

st.set_page_config(page_title="Foto Fade-In Quiz", layout="centered")

st.title("📸 Foto Onthul Quiz: Fade-in")

# --- Initialisatie van Session State ---
if 'playing' not in st.session_state:
    st.session_state.playing = False
if 'paused' not in st.session_state:
    st.session_state.paused = False
if 'alpha' not in st.session_state:
    st.session_state.alpha = 0.0  
if 'photo_index' not in st.session_state:
    st.session_state.photo_index = 0

# --- Sidebar Instellingen ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    
    # Keuze voor achtergrondkleur
    bg_color = st.radio("Startkleur (Fade vanuit):", ["Wit", "Zwart"])
    bg_value = 255 if bg_color == "Wit" else 0
    
    speed = st.slider("Snelheid van verschijnen", 0.005, 0.1, 0.02, help="Lager is langzamer")
    uploaded_files = st.file_uploader("Upload foto's", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    # Knoppen layout
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("▶️ Start / Reset"):
            st.session_state.alpha = 0.0
            st.session_state.playing = True
            st.session_state.paused = False

    with col2:
        if st.button("⏸️ Pauze / Hervat"):
            st.session_state.paused = not st.session_state.paused

    with col3:
        if st.button("⏹️ Stop Quiz"):
            st.session_state.playing = False
            st.session_state.alpha = 0.0

    with col4:
        if st.button("⏭️ Volgende"):
            st.session_state.photo_index = (st.session_state.photo_index + 1) % len(uploaded_files)
            st.session_state.alpha = 0.0
            st.session_state.playing = False

    # Foto inladen
    img = Image.open(uploaded_files[st.session_state.photo_index]).convert("RGB")
    img_array = np.array(img).astype(float)
    
    placeholder = st.empty()

    # Logica voor het faden
    if st.session_state.playing and not st.session_state.paused:
        while st.session_state.alpha < 1.0:
            if st.session_state.paused:
                break
                
            st.session_state.alpha += speed
            if st.session_state.alpha > 1.0:
                st.session_state.alpha = 1.0

            # Bereken het beeld: mix tussen bg_value (0 of 255) en de originele foto
            fade_img = ((1.0 - st.session_state.alpha) * bg_value + st.session_state.alpha * img_array).astype(np.uint8)
            
            placeholder.image(fade_img, use_container_width=True)
            time.sleep(0.05) 
            
            if st.session_state.alpha >= 1.0:
                st.success("Foto volledig zichtbaar.")
                st.session_state.playing = False
    else:
        # Statische weergave bij pauze of stop
        fade_img = ((1.0 - st.session_state.alpha) * bg_value + st.session_state.alpha * img_array).astype(np.uint8)
        caption = f"Modus: {bg_color} Fade"
        placeholder.image(fade_img, caption=caption, use_container_width=True)

else:
    st.info("Upload eerst foto's in de zijbalk.")
