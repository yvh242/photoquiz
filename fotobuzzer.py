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

with st.sidebar:
    st.title("⚙️ Configuratie")
    role = st.radio("Kies je rol:", ["Team", "Host"])

if role == "Host":
    status = get_status()
    with st.sidebar:
        st.divider()
        st.header("🎮 Admin Panel")
        
        # ONDERWERP
        current_subject = st.text_input("Onderwerp:", value=status.get("subject", ""))
        if st.button("Update Onderwerp"):
            update_db(subject=current_subject)
            
        uploaded_files = st.file_uploader("Upload foto's", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        
        st.divider()
        st.subheader("Spelbediening")
        grid_size = st.slider("Raster grootte", 4, 30, 10)
        delay = st.slider("Snelheid (sec)", 0.05, 2.0, 0.4)
        
        if st.button("▶️ START RONDE", use_container_width=True):
            if uploaded_files:
                total_cells = grid_size * grid_size
                order = list(range(total_cells))
                random.shuffle(order)
                update_db(winner=None, active=True, revealed=[], order=order, excluded_teams=[], game_started=True, show_all=False)
                st.rerun()

        if st.button("👁️ ONTHUL VOLLEDIG", use_container_width=True):
            update_db(show_all=True, active=False)
            st.rerun()

        # UITSCHAKELEN VAN TEAMS (Alleen zichtbaar als er een winnaar is)
        if status.get("winner"):
            st.warning(f"Winnaar: {status['winner']}")
            if st.button(f"❌ {status['winner']} FOUT (Uitsluiten)", use_container_width=True):
                excluded = status.get("excluded_teams", [])
                if status["winner"] not in excluded:
                    excluded.append(status["winner"])
                update_db(winner=None, active=True, excluded_teams=excluded)
                st.rerun()

        if st.button("⏭️ VOLGENDE FOTO", use_container_width=True):
            if uploaded_files:
                st.session_state.photo_idx = (st.session_state.get('photo_idx', 0) + 1) % len(uploaded_files)
                update_db(winner=None, active=False, revealed=[], order=[], excluded_teams=[], game_started=False, show_all=False)
                st.rerun()

        st.divider()
        # TEAM BEHEER & LIST
        with st.expander("👥 Team Beheer & Ingelogde Teams", expanded=True):
            teams = status.get("connected_teams", [])
            excluded = status.get("excluded_teams", [])
            
            if teams:
                st.write("**Ingelogde teams:**")
                for t in teams:
                    status_text = "🚫 (Uitgesloten)" if t in excluded else "✅ (Actief)"
                    st.write(f"- {t} {status_text}")
                
                st.divider()
                team_to_remove = st.selectbox("Verwijder team uit database:", [""] + teams)
                if st.button("Verwijder geselecteerd team") and team_to_remove:
                    new_teams = [t for t in teams if t != team_to_remove]
                    update_db(connected_teams=new_teams)
                    st.rerun()
                
                if st.button("Wis alle teams"):
                    update_db(connected_teams=[])
                    st.rerun()
            else:
                st.write("Nog geen teams verbonden.")

    # --- HOOFDSCHERM (Host / Presentatie) ---
    st.title("📸 Foto Blokjes Quiz")
    if status.get("subject"):
        st.markdown(f"<h1 style='text-align: center; color: #FF4B4B;'>{status['subject']}</h1>", unsafe_allow_html=True)

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
                placeholder.image(img_array * 0, caption="Wachten op de host...", use_container_width=True)
            else:
                placeholder.image(temp_img, use_container_width=True)
            
            if status.get("winner"):
                st.markdown(f"<div style='text-align: center; background-color: #2E7D32; padding: 20px; border-radius: 10px;'>"
                            f"<h2 style='color: white; margin: 0;'>🏆 {status['winner']} mag antwoorden!</h2>"
                            f"</div>", unsafe_allow_html=True)
    else:
        st.info("Upload foto's in de zijbalk.")

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
        if status.get("subject"): st.info(f"Categorie: {status['subject']}")
        
        if team_name_input not in status.get("connected_teams", []):
             st.warning("Je bent verwijderd door de host.")
             st.session_state.my_team_name = ""
             st.rerun()

        if team_name_input in status.get("excluded_teams", []):
            st.error("❌ Je bent uitgesloten voor deze foto.")
        elif not status.get("game_started"):
            st.info("De host start zo de ronde...")
        elif status.get("winner"):
            if status["winner"] == team_name_input:
                st.success("JULLIE ZIJN EERST!")
            else:
                st.warning(f"{status['winner']} heeft gebuzzerd!")
        else:
            if st.button("🚨 BUZZER 🚨", use_container_width=True):
                update_db(winner=team_name_input)
                st.rerun()
        time.sleep(1)
        st.rerun()
