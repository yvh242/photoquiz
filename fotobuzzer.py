import streamlit as st
import PIL.Image as Image
import numpy as np
import random
import time
import json
import os

# --- Database Instellingen ---
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
    for _ in range(5):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            time.sleep(0.1)
    return {}

def update_db(**kwargs):
    status = get_status()
    if not status: return 
    for key, value in kwargs.items():
        if key == "connected_teams":
            if isinstance(value, str):
                if value not in status.get("connected_teams", []):
                    status.setdefault("connected_teams", []).append(value)
            else:
                status["connected_teams"] = value
        else:
            status[key] = value
    for _ in range(5):
        try:
            with open(DB_FILE + ".tmp", "w") as f:
                json.dump(status, f)
            os.replace(DB_FILE + ".tmp", DB_FILE)
            break
        except IOError:
            time.sleep(0.1)

init_db()

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Configuratie")
    role = st.radio("Kies je rol:", ["Team", "Host"])

if role == "Host":
    status = get_status()
    
    with st.sidebar:
        st.divider()
        st.header("🎮 Instellingen")
        current_subject = st.text_input("Onderwerp:", value=status.get("subject", ""))
        if st.button("Update Onderwerp"):
            update_db(subject=current_subject)
            
        uploaded_files = st.file_uploader("Upload foto's", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="uploader")
        grid_size = st.slider("Raster grootte", 4, 30, 10)
        delay = st.slider("Snelheid (sec)", 0.05, 2.0, 0.4)
        
        st.divider()
        if st.button("🔥 VOLLEDIGE RESET", use_container_width=True):
            init_db(force=True)
            if 'photo_idx' in st.session_state: del st.session_state.photo_idx
            st.rerun()

        st.subheader("👥 Teams")
        if st.button("🔄 Ververs Teamlijst"):
            st.rerun()
            
        teams = status.get("connected_teams", [])
        if teams:
            for t in teams:
                icon = "🚫" if t in status.get("excluded_teams", []) else "✅"
                st.write(f"{icon} {t}")
        else:
            st.write("Geen teams.")

    # --- HOOFDSCHERM ---
    st.title("📸 Foto Blokjes Quiz")
    
    if status.get("subject"):
        st.markdown(f"<h1 style='text-align: center; color: #FF4B4B;'>{status['subject']}</h1>", unsafe_allow_html=True)

    if uploaded_files:
        # --- KNOPPEN BOVEN DE FOTO ---
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("▶️ START RONDE", use_container_width=True):
                total_cells = grid_size * grid_size
                order = list(range(total_cells))
                random.shuffle(order)
                update_db(winner=None, active=True, revealed=[], order=order, excluded_teams=[], game_started=True, show_all=False)
                st.rerun()
        with col2:
            if st.button("👁️ ONTHUL ALLES", use_container_width=True):
                update_db(show_all=True, active=False)
                st.rerun()
        with col3:
            if st.button("⏭️ VOLGENDE", use_container_width=True):
                st.session_state.photo_idx = (st.session_state.get('photo_idx', 0) + 1) % len(uploaded_files)
                update_db(winner=None, active=False, revealed=[], order=[], excluded_teams=[], game_started=False, show_all=False)
                st.rerun()

        # Fout-knop alleen tonen als er een winnaar is
        if status.get("winner"):
            if st.button(f"❌ {status['winner']} had het FOUT (Uitsluiten & Verder)", use_container_width=True):
                excluded = status.get("excluded_teams", [])
                if status["winner"] not in excluded:
                    excluded.append(status["winner"])
                update_db(winner=None, active=True, excluded_teams=excluded)
                st.rerun()

        # --- FOTO DISPLAY ---
        photo_idx = st.session_state.get('photo_idx', 0)
        if photo_idx >= len(uploaded_files): photo_idx = 0
        
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
                if current_status.get("winner") or current_status.get("show_all") or not current_status.get("game_started"):
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
                placeholder.image(img_array * 0, caption="Klik op START RONDE om te beginnen", use_container_width=True)
            else:
                placeholder.image(temp_img, use_container_width=True)
            
            if status.get("winner"):
                st.success(f"🏆 {status['winner']} mag antwoorden!")
    else:
        st.info("Upload eerst foto's in de zijbalk.")

else:
    # --- TEAM INTERFACE ---
    st.title("🚨 Team Buzzer")
    if "my_team_name" not in st.session_state:
        st.session_state.my_team_name = ""
    team_name_input = st.text_input("Teamnaam:", value=st.session_state.my_team_name)
    if team_name_input:
        st.session_state.my_team_name = team_name_input
        update_db(connected_teams=team_name_input)
        status = get_status()
        
        if team_name_input not in status.get("connected_teams", []):
            st.session_state.my_team_name = ""
            st.rerun()

        if status.get("subject"): st.info(f"Categorie: {status['subject']}")
        if team_name_input in status.get("excluded_teams", []):
            st.error("❌ Helaas, je bent uitgeschakeld voor deze foto.")
        elif not status.get("game_started"):
            st.info("De host maakt de foto klaar...")
        elif status.get("winner"):
            if status["winner"] == team_name_input:
                st.success("JULLIE ZIJN EERST!")
            else:
                st.warning(f"{status['winner']} is aan de beurt...")
        else:
            if st.button("🚨 BUZZER 🚨", use_container_width=True):
                update_db(winner=team_name_input)
                st.rerun()
        
        time.sleep(1)
        st.rerun()
