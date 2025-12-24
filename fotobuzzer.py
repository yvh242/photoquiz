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
            json.dump({"winner": None, "active": False, "revealed": []}, f)

def get_status():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def set_buzzer_winner(team_name):
    status = get_status()
    if status["active"] and status["winner"] is None:
        status["winner"] = team_name
        with open(DB_FILE, "w") as f:
            json.dump(status, f)
        return True
    return False

def update_db(winner=None, active=None, revealed=None):
    status = get_status()
    if winner is not None: status["winner"] = winner
    if active is not None: status["active"] = active
    if revealed is not None: status["revealed"] = revealed
    with open(DB_FILE, "w") as f:
        json.dump(status, f)

init_db()

# --- Sidebar ---
st.sidebar.title("Instellingen")
role = st.sidebar.radio("Kies je rol:", ["Team", "Host"])

if role == "Host":
    st.title("Admin Panel - Foto Blokjes Quiz")
    
    with st.sidebar:
        grid_size = st.slider("Raster grootte", 4, 20, 10)
        delay = st.slider("Snelheid (sec)", 0.1, 2.0, 0.5)
        uploaded_files = st.file_uploader("Upload foto's", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    if uploaded_files:
        if 'photo_idx' not in st.session_state:
            st.session_state.photo_idx = 0
        
        img = Image.open(uploaded_files[st.session_state.photo_idx]).convert("RGB")
        img_array = np.array(img)
        h, w, _ = img_array.shape
        cell_h, cell_w = h // grid_size, w // grid_size
        total_cells = grid_size * grid_size

        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start Animatie & Buzzer"):
                order = list(range(total_cells))
                random.shuffle(order)
                st.session_state.order = order
                update_db(winner=None, active=True, revealed=[])
        with col2:
            if st.button("⏭️ Volgende Foto"):
                st.session_state.photo_idx = (st.session_state.photo_idx + 1) % len(uploaded_files)
                update_db(winner=None, active=False, revealed=[])
                st.rerun()

        placeholder = st.empty()
        status = get_status()

        # Animatie Loop
        if status["active"] and status["winner"] is None:
            revealed = status["revealed"]
            for i in range(len(revealed), len(st.session_state.order)):
                # Check tussentijds of iemand gedrukt heeft
                current_status = get_status()
                if current_status["winner"]:
                    break
                
                revealed.append(st.session_state.order[i])
                update_db(revealed=revealed)
                
                # Teken foto
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
                st.balloons()
                st.header(f"🏆 {status['winner']} drukte eerst!")

else:
    # --- Team Interface ---
    st.title("Team Buzzer")
    team_name = st.text_input("Teamnaam:", placeholder="Bijv. Team Opa")
    
    if team_name:
        status = get_status()
        if not status["active"]:
            st.info("Wacht op de Host om de ronde te starten...")
            time.sleep(1)
            st.rerun()
        elif status["winner"]:
            if status["winner"] == team_name:
                st.success("JIJ BENT EERST! Geef je antwoord!")
            else:
                st.error(f"Te laat! {status['winner']} was eerst.")
            time.sleep(2)
            st.rerun()
        else:
            if st.button("🚨 IK WEET HET! 🚨", use_container_width=True):
                set_buzzer_winner(team_name)
                st.rerun()
        
        time.sleep(0.5)
        st.rerun()
