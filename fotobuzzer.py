import streamlit as st
import PIL.Image as Image
import numpy as np
import random
import time
import json
import os

# --- Database Instellingen ---
DB_FILE = "quiz_state.json"

def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"winner": None, "active": False, "revealed": [], "order": []}, f)

def get_status():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def update_db(**kwargs):
    status = get_status()
    for key, value in kwargs.items():
        status[key] = value
    with open(DB_FILE, "w") as f:
        json.dump(status, f)

init_db()

# --- Sidebar ---
st.sidebar.title("Instellingen")
role = st.sidebar.radio("Kies je rol:", ["Team", "Host"])

if role == "Host":
    st.title("Admin Panel - Foto Blokjes Quiz")
    
    with st.sidebar:
        grid_size = st.slider("Raster grootte", 4, 30, 10)
        delay = st.slider("Snelheid (sec)", 0.05, 2.0, 0.4)
        uploaded_files = st.file_uploader("Upload foto's", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    if uploaded_files:
        if 'photo_idx' not in st.session_state:
            st.session_state.photo_idx = 0
        
        img = Image.open(uploaded_files[st.session_state.photo_idx]).convert("RGB")
        img_array = np.array(img)
        h, w, _ = img_array.shape
        cell_h, cell_w = h // grid_size, w // grid_size
        total_cells = grid_size * grid_size

        status = get_status()

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("▶️ Start / Reset Ronde"):
                order = list(range(total_cells))
                random.shuffle(order)
                update_db(winner=None, active=True, revealed=[], order=order)
                st.rerun()
        
        with col2:
            if st.button("🔄 Fout! (Doorgaan)"):
                # Reset alleen de winnaar, laat de rest (revealed en order) staan
                update_db(winner=None, active=True)
                st.rerun()

        with col3:
            if st.button("⏭️ Volgende Foto"):
                st.session_state.photo_idx = (st.session_state.photo_idx + 1) % len(uploaded_files)
                update_db(winner=None, active=False, revealed=[], order=[])
                st.rerun()

        placeholder = st.empty()

        # Animatie logica voor de Host
        if status["active"] and status["winner"] is None:
            revealed = status["revealed"]
            order = status["order"]
            
            # Ga verder vanaf het punt waar we gebleven waren
            start_index = len(revealed)
            for i in range(start_index, len(order)):
                # Check elke stap of er een winnaar is (via de DB)
                current_status = get_status()
                if current_status["winner"]:
                    st.rerun() # Stop animatie en toon winnaar
                
                revealed.append(order[i])
                update_db(revealed=revealed)
                
                # Teken de foto
                temp_img = np.zeros_like(img_array)
                for idx in revealed:
                    r, c = divmod(idx, grid_size)
                    temp_img[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w] = \
                        img_array[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
                
                placeholder.image(temp_img, use_container_width=True)
                time.sleep(delay)
        else:
            # Stilstaand beeld tonen
            temp_img = np.zeros_like(img_array)
            for idx in status["revealed"]:
                r, c = divmod(idx, grid_size)
                temp_img[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w] = \
                    img_array[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
            
            placeholder.image(temp_img if status["revealed"] else img_array * 0, use_container_width=True)
            
            if status["winner"]:
                st.header(f"🏆 {status['winner']} mag antwoorden!")
                st.warning("De animatie is gepauzeerd. Gebruik 'Fout!' om door te gaan of 'Volgende' voor een nieuwe foto.")

else:
    # --- Team Interface ---
    st.title("Team Buzzer")
    team_name = st.text_input("Teamnaam:", placeholder="Bijv. Familie Janssen")
    
    if team_name:
        status = get_status()
        if not status["active"]:
            st.info("Wacht op de Host...")
        elif status["winner"]:
            if status["winner"] == team_name:
                st.success("JULLIE ZIJN EERST!")
            else:
                st.error(f"Te laat! {status['winner']} was eerst.")
        else:
            if st.button("🚨 IK WEET HET! 🚨", use_container_width=True):
                # Check nogmaals in de DB vlak voor het schrijven
                s = get_status()
                if s["winner"] is None:
                    update_db(winner=team_name)
                st.rerun()
        
        # Team pagina ververst elke seconde om de status van de host te volgen
        time.sleep(1)
        st.rerun()
