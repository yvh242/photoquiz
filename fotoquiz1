import streamlit as st
import PIL.Image as Image
import numpy as np
import random
import time

st.set_page_config(page_title="Foto Onthul Spel", layout="centered")

st.title("📸 Foto Onthul Spel")
st.write("Upload een foto en raad wat er verschijnt.")

# --- Sidebar Instellingen ---
with st.sidebar:
    st.header("Instellingen")
    grid_size = st.slider("Raster grootte (n x n)", 2, 20, 5)
    delay = st.slider("Snelheid (seconden per vakje)", 0.1, 3.0, 1.0)
    uploaded_files = st.file_uploader("Upload foto's", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    # Kies een foto uit de lijst (bijv. de eerste of een willekeurige)
    if 'photo_index' not in st.session_state:
        st.session_state.photo_index = 0
    
    img = Image.open(uploaded_files[st.session_state.photo_index])
    img = img.convert("RGB")
    
    # Maak de foto vierkant of passend voor het raster
    img_array = np.array(img)
    h, w, _ = img_array.shape
    
    # Bereken vakjes
    cell_h = h // grid_size
    cell_w = w // grid_size
    
    # Maak een lijst met alle coördinaten van het raster
    indices = [(r, c) for r in range(grid_size) for c in range(grid_size)]
    
    if st.button("Start Quiz / Volgende Foto"):
        # Reset het spel
        random.shuffle(indices)
        
        # Maak een zwart canvas (masker)
        mask = np.zeros_like(img_array)
        placeholder = st.empty()
        
        for r, c in indices:
            # Kopieer het originele deel van de foto naar het zwarte canvas
            mask[r*cell_h : (r+1)*cell_h, c*cell_w : (c+1)*cell_w] = \
                img_array[r*cell_h : (r+1)*cell_h, c*cell_w : (c+1)*cell_w]
            
            # Toon de huidige status
            placeholder.image(mask, caption="Wie of wat is dit?", use_container_width=True)
            
            # Wacht de ingestelde tijd
            time.sleep(delay)
            
        st.success("Foto volledig onthuld!")
        if st.session_state.photo_index < len(uploaded_files) - 1:
            st.session_state.photo_index += 1
        else:
            st.session_state.photo_index = 0
            st.info("Alle foto's zijn geweest.")

else:
    st.info("Upload eerst een of meerdere foto's in de zijbalk om te beginnen.")
