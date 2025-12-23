import streamlit as st
import PIL.Image as Image
import numpy as np
import random
import time

st.set_page_config(page_title="Foto Quiz", layout="centered")

st.title("📸 Foto Onthul Quiz")

# --- Initialisatie van Session State ---
if 'playing' not in st.session_state:
    st.session_state.playing = False
if 'paused' not in st.session_state:
    st.session_state.paused = False
if 'photo_index' not in st.session_state:
    st.session_state.photo_index = 0
if 'revealed_indices' not in st.session_state:
    st.session_state.revealed_indices = []
if 'order' not in st.session_state:
    st.session_state.order = []

# --- Sidebar Instellingen ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    grid_size = st.slider("Raster grootte (n x n)", 2, 30, 10)
    delay = st.slider("Snelheid (sec per vakje)", 0.05, 2.0, 0.5)
    uploaded_files = st.file_uploader("Upload foto's", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    # Knoppen layout
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("▶️ Start / Reset"):
            st.session_state.playing = True
            st.session_state.paused = False
            st.session_state.revealed_indices = []
            # Maak een nieuwe volgorde van onthullen
            total_cells = grid_size * grid_size
            st.session_state.order = list(range(total_cells))
            random.shuffle(st.session_state.order)

    with col2:
        if st.button("⏸️ Pauze / Hervat"):
            st.session_state.paused = not st.session_state.paused

    with col3:
        if st.button("⏹️ Stop Quiz"):
            st.session_state.playing = False
            st.session_state.revealed_indices = []

    with col4:
        if st.button("⏭️ Volgende"):
            st.session_state.photo_index = (st.session_state.photo_index + 1) % len(uploaded_files)
            st.session_state.revealed_indices = []
            st.session_state.playing = False # Stop even voor de nieuwe foto

    # Foto verwerken
    img = Image.open(uploaded_files[st.session_state.photo_index]).convert("RGB")
    img_array = np.array(img)
    h, w, _ = img_array.shape
    cell_h, cell_w = h // grid_size, w // grid_size

    placeholder = st.empty()

    # Logica voor het onthullen
    if st.session_state.playing and not st.session_state.paused:
        # Zolang er nog vakjes onthuld moeten worden
        while len(st.session_state.revealed_indices) < len(st.session_state.order):
            if st.session_state.paused: # Check tijdens loop of er op pauze is gedrukt
                break
                
            # Voeg volgende index toe uit de shuffle
            next_idx = st.session_state.order[len(st.session_state.revealed_indices)]
            st.session_state.revealed_indices.append(next_idx)

            # Masker opbouwen
            display_img = np.zeros_like(img_array)
            for idx in st.session_state.revealed_indices:
                r, c = divmod(idx, grid_size)
                display_img[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w] = \
                    img_array[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
            
            placeholder.image(display_img, use_container_width=True)
            time.sleep(delay)
            
            # Forceer update (nodig in loops binnen Streamlit)
            if len(st.session_state.revealed_indices) == len(st.session_state.order):
                st.success("Foto onthuld!")
                st.balloons()
                st.session_state.playing = False
    else:
        # Statische weergave (als het spel op pauze staat of gestopt is)
        display_img = np.zeros_like(img_array)
        for idx in st.session_state.revealed_indices:
            r, c = divmod(idx, grid_size)
            display_img[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w] = \
                img_array[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
        
        caption = "Gepauzeerd" if st.session_state.paused else "Druk op Start"
        placeholder.image(display_img if st.session_state.revealed_indices else img_array * 0, caption=caption, use_container_width=True)

else:
    st.info("Upload eerst foto's in de zijbalk.")
