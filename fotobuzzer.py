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
            "game_started": False  # Nieuwe vlag om start te forceren
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
        
        current_subject = st.text_input("Onderwerp van de ronde:", value=status.get("subject", ""))
        if st.button("Update Onderwerp"):
            update_db(subject=current_subject)
            
        uploaded_files = st.file_uploader("Upload foto's", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        
        st.divider()
        st.subheader("Bediening")
        grid_size = st.slider("Raster grootte", 4, 30, 10)
        delay = st.slider("Snelheid (sec)", 0.05, 2.0, 0.4)
        
        if st.button("▶️ START / RESET RONDE", use_container_width=True):
            if uploaded_files:
                total_cells = grid_size * grid_size
                order = list(range(total_cells))
                random.shuffle(order)
                # Zet game_started op True en active op True
                update_db(winner=None, active=True, revealed=[], order=order, excluded_teams=[], game_started=True)
                st.rerun()

        if st.button("❌ FOUT! (Team uitsluiten)", use_container_width=True):
            if status.get("winner"):
                excluded = status.get("excluded_teams", [])
                if status["winner"] not in excluded:
                    excluded.append(status["winner"])
                update_db(winner=None, active=True, excluded_teams=excluded)
            st.rerun()

        if st.button("⏭️ VOLGENDE FOTO", use_container_width=True):
            if uploaded_files:
                st.session_state.photo_idx = (st.session_state.get('photo_idx', 0) + 1) % len(uploaded_files)
                # Zet game_started weer op False voor de nieuwe foto
                update_db(winner=None, active=False, revealed=[], order=[], excluded_teams=[], game_started=False)
                st.rerun()

        st.divider()
        with st.expander("👥 Team Beheer"):
            teams = status.get("connected_teams", [])
            if teams:
                team_to_remove = st.selectbox("Team verwijderen:", [""] + teams)
                if st.button("Verwijder team") and team_to_remove:
                    new_teams = [t for t in teams if t != team_to_remove]
                    update_db(connected_teams=new_teams)
                    st.rerun()
                if st.button("Wis alle teams"):
                    update_db(connected_teams=[])
                    st.rerun()

    # --- HOOFDSCHERM ---
    st.title("📸 Foto Blokjes Quiz")
    
    if status.get("subject"):
        st.markdown(f"<h1 style='text-align: center; color: #FF4B4B;'>Categorie: {status['subject']}</h1>", unsafe_allow_html=True)

    if uploaded_files:
        if 'photo_idx' not in st.session_state:
            st.session_state.photo_idx = 0
        
        img = Image.open(uploaded_files[st.session_state.photo_idx]).convert("RGB")
        img_array = np.array(img)
        h, w, _ = img_array.shape
        cell_h, cell_w = h // grid_size, w // grid_size
        
        placeholder = st.empty()

        # Toon alleen de animatie als game_started op True staat
        if status.get("game_started") and status.get("active") and status.get("winner") is None:
            revealed = status.get("revealed", [])
            order = status.get("order", [])
            
            for i in range(len(revealed), len(order)):
                current_status = get_status()
                if current_status.get("winner"):
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
            # Als het spel nog niet gestart is, of er is een winnaar, of het is gepauzeerd:
            temp_img = np.zeros_like(img_array)
            # Vul het beeld alleen met reeds onthulde blokjes
            for idx in status.get("revealed", []):
                r, c = divmod(idx, grid_size)
                temp_img[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w] = \
                    img_array[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
            
            # Als er nog niets onthuld is en game_started is False, toon zwart (of een placeholder)
            if not status.get("revealed") and not status.get("game_started"):
                st.info("Klaar voor de start... Druk op START in het Admin Panel.")
                placeholder.image(img_array * 0, use_container_width=True)
            else:
                placeholder.image(temp_img, use_container_width=True)
            
            if status.get("winner"):
                st.markdown(f"<div style='text-align: center; background-color: #2E7D32; padding: 20px; border-radius: 10px;'>"
                            f"<h2 style='color: white; margin: 0;'>🏆 {status['winner']} mag antwoorden!</h2>"
                            f"</div>", unsafe_allow_html=True)
    else:
        st.info("Upload foto's in de zijbalk om te beginnen.")

else:
    # --- TEAM INTERFACE (ONGEWIJZIGD) ---
    st.title("🚨 Team Buzzer")
    # ... (rest van de team code blijft hetzelfde als in de vorige stap)
    if "my_team_name" not in st.session_state:
        st.session_state.my_team_name = ""
    team_name_input = st.text_input("Vul je teamnaam in:", value=st.session_state.my_team_name)
    if team_name_input:
        st.session_state.my_team_name = team_name_input
        update_db(connected_teams=team_name_input)
        status = get_status()
        if team_name_input not in status.get("connected_teams", []):
            st.session_state.my_team_name = ""
            st.rerun()
        if status.get("subject"):
            st.info(f"Categorie: {status['subject']}")
        if team_name_input in status.get("excluded_teams", []):
            st.error("❌ Helaas, fout antwoord! Wacht op de volgende foto.")
        elif not status.get("game_started"): # Team ziet nu ook dat het spel nog niet gestart is
            st.info("De host maakt de foto klaar...")
        elif status.get("winner"):
            if status["winner"] == team_name_input:
                st.success("JULLIE ZIJN EERST!")
            else:
                st.warning(f"{status['winner']} is aan de beurt...")
        else:
            if st.button("🚨 BUZZER 🚨", use_container_width=True):
                s = get_status()
                if s.get("winner") is None:
                    update_db(winner=team_name_input)
                st.rerun()
        time.sleep(1)
        st.rerun()
