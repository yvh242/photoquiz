import streamlit as st
import PIL.Image as Image
import numpy as np
import random
import time
import json
import os

# --- DATABASE CONFIGURATIE ---
DB_FILE = "quiz_state.json"

def init_db(force=False):
    if not os.path.exists(DB_FILE) or force:
        data = {
            "winner": None, 
            "active": False, 
            "revealed": [], 
            "order": [], 
            "excluded_teams": [],
            "connected_teams": [],
            "subject": "",
            "game_started": False,
            "show_all": False
        }
        with open(DB_FILE, "w") as f:
            json.dump(data, f)

def get_status():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def update_db(**kwargs):
    status = get_status()
    if not status: return 
    for key, value in kwargs.items():
        if key == "connected_teams":
            if value not in status.get("connected_teams", []):
                status.setdefault("connected_teams", []).append(value)
        else:
            status[key] = value
    with open(DB_FILE, "w") as f:
        json.dump(status, f)

init_db()

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Quiz Master")
    role = st.radio("Kies je rol:", ["Team", "Host"])

if role == "Host":
    status = get_status()
    with st.sidebar:
        st.divider()
        st.header("🎮 Admin Bediening")
        
        # Invoer velden
        current_subject = st.text_input("Onderwerp:", value=status.get("subject", ""))
        if st.button("Update Onderwerp"):
            update_db(subject=current_subject)
            
        uploaded_files = st.file_uploader("Upload foto's", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        
        grid_size = st.slider("Raster grootte", 4, 30, 10)
        delay = st.slider("Snelheid (sec)", 0.05, 1.0, 0.3)
        
        st.divider()
        # Actie knoppen
        if st.button("▶️ START / RESET RONDE", use_container_width=True):
            if uploaded_files:
                total_cells = grid_size * grid_size
                order = list(range(total_cells))
                random.shuffle(order)
                update_db(winner=None, active=True, revealed=[], order=order, excluded_teams=[], game_started=True, show_all=False)
                st.rerun()

        if st.button("👁️ ONTHUL VOLLEDIG", use_container_width=True):
            update_db(show_all=True, active=False)
            st.rerun()

        if st.button("⏭️ VOLGENDE FOTO", use_container_width=True):
            if uploaded_files:
                if 'photo_idx' not in st.session_state: st.session_state.photo_idx = 0
                st.session_state.photo_idx = (st.session_state.photo_idx + 1) % len(uploaded_files)
                update_db(winner=None, active=False, revealed=[], order=[], excluded_teams=[], game_started=False, show_all=False)
                st.rerun()

        st.divider()
        # Team beheer
        if st.button("🔥 RESET ALLES (Wist Teams & Foto's)"):
            init_db(force=True)
            if 'photo_idx' in st.session_state: del st.session_state.photo_idx
            st.rerun()
            
        st.write("**Verbonden Teams:**")
        for t in status.get("connected_teams", []):
            st.write(f"- {t}")

    # --- HOOFDSCHERM HOST ---
    st.title("📸 Foto Blokjes Quiz")
    
    if status.get("subject"):
        st.markdown(f"<h1 style='text-align: center; color: red;'>{status['subject']}</h1>", unsafe_allow_html=True)

    if uploaded_files:
        photo_idx = st.session_state.get('photo_idx', 0)
        img = Image.open(uploaded_files[photo_idx]).convert("RGB")
        img_array = np.array(img)
        h, w, _ = img_array.shape
        cell_h, cell_w = h // grid_size, w // grid_size
        placeholder = st.empty()

        if status.get("show_all"):
            placeholder.image(img_array, use_container_width=True)
        elif status.get("game_started") and status.get("active") and status.get("winner") is None:
            revealed = status.get("revealed", [])
            order = status.get("order", [])
            for i in range(len(revealed), len(order)):
                current_status = get_status()
                if current_status.get("winner") or current_status.get("show_all"):
                    st.rerun() 
                revealed.append(order[i])
                update_db(revealed=revealed)
                temp_img = np.zeros_like(img_array)
                for idx in revealed:
                    r, c = divmod(idx, grid_size)
                    temp_img[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w] = img_array[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
                placeholder.image(temp_img, use_container_width=True)
                time.sleep(delay)
        else:
            temp_img = np.zeros_like(img_array)
            for idx in status.get("revealed", []):
                r, c = divmod(idx, grid_size)
                temp_img[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w] = img_array[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
            
            if not status.get("game_started") and not status.get("show_all"):
                placeholder.image(img_array * 0, caption="Wacht op de Host...", use_container_width=True)
            else:
                placeholder.image(temp_img, use_container_width=True)
            
            if status.get("winner"):
                st.success(f"🏆 {status['winner']} mag antwoorden!")
                if st.button(f"❌ {status['winner']} had het fout", use_container_width=True):
                    excluded = status.get("excluded_teams", [])
                    excluded.append(status["winner"])
                    update_db(winner=None, active=True, excluded_teams=excluded)
                    st.rerun()
    else:
        st.info("Upload foto's in de zijbalk om te beginnen.")

else:
    # --- TEAM INTERFACE ---
    st.title("🚨 Team Buzzer")
    my_name = st.text_input("Voer je teamnaam in:")
    if my_name:
        update_db(connected_teams=my_name)
        status = get_status()
        
        if my_name in status.get("excluded_teams", []):
            st.error("Je bent uitgesloten voor deze foto.")
        elif status.get("winner"):
            st.warning(f"{status['winner']} antwoordt...")
        elif not status.get("game_started"):
            st.info("De ronde start zo...")
        else:
            if st.button("🚨 IK WEET HET! 🚨", use_container_width=True):
                update_db(winner=my_name)
                st.rerun()
        time.sleep(1)
        st.rerun()
