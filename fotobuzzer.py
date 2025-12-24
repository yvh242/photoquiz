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
            json.dump({"winner": None, "active": False, "revealed": [], "order": [], "excluded_teams": []}, f)

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
            if st.button("▶️ Start / Volledige Reset"):
                order = list(range(total_cells))
                random.shuffle(order)
                update_db(winner=None, active=True, revealed=[], order=order, excluded_teams=[])
                st.rerun()
        
        with col2:
            if st.button("❌ Fout! (Team uitsluiten)"):
                if status["winner"]:
                    excluded = status.get("excluded_teams", [])
                    if status["winner"] not in excluded:
                        excluded.append(status["winner"])
                    update_db(winner=None, active=True, excluded_teams=excluded)
                st.rerun()

        with col3:
            if st.button("⏭️ Volgende Foto"):
                st.session_state.photo_idx = (st.session_state.photo_idx + 1) % len(uploaded_files)
                update_db(winner=None, active=False, revealed=[], order=[], excluded_teams=[])
                st.rerun()

        if status.get("excluded_teams"):
            st.write(f"🚫 **Uitgesloten deze ronde:** {', '.join(status['excluded_teams'])}")

        placeholder = st.empty()

        # Animatie logica voor de Host
        if status["active"] and status["winner"] is None:
            revealed = status["revealed"]
            order = status["order"]
            
            for i in range(len(revealed), len(order)):
                current_status = get_status()
                if current_status["winner"]:
                    st.rerun() 
                
                revealed.append(order[i])
                update_db(revealed=revealed)
                
                temp_img = np.zeros_like(img_array)
                for idx in revealed:
                    r, c = divmod(idx, grid_size)
                    temp_img[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w] = \
                        img_array[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
                
                placeholder.image(temp_img, use_container_width=True)
                time.sleep(delay)
        else:
            temp_img = np.zeros_like(img_array)
            for idx in status["revealed"]:
                r, c = divmod(idx, grid_size)
                temp_img[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w] = \
                    img_array[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
            
            placeholder.image(temp_img if status["revealed"] else img_array * 0, use_container_width=True)
            
            if status["winner"]:
                st.header(f"🏆 {status['winner']} mag antwoorden!")
                st.info("Klik op 'Fout!' om dit team uit te sluiten en de foto verder te laten gaan.")

else:
    # --- Team Interface ---
    st.title("Team Buzzer")
    team_name = st.text_input("Teamnaam:", placeholder="Bijv. Kleinkinderen")
    
    if team_name:
        status = get_status()
        excluded_teams = status.get("excluded_teams", [])

        if team_name in excluded_teams:
            st.error("❌ Je hebt een fout antwoord gegeven. Je mag bij deze foto niet meer buzzen.")
        elif not status["active"]:
            st.info("Wacht op de Host...")
        elif status["winner"]:
            if status["winner"] == team_name:
                st.success("JULLIE ZIJN EERST!")
            else:
                st.warning(f"{status['winner']} is aan het antwoorden...")
        else:
            if st.button("🚨 IK WEET HET! 🚨", use_container_width=True):
                s = get_status()
                if s["winner"] is None and team_name not in s.get("excluded_teams", []):
                    update_db(winner=team_name)
                st.rerun()
        
        time.sleep(1)
        st.rerun()
