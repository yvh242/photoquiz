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
            "subject": ""
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
            # Als value een string is (nieuw team), voeg toe
            if isinstance(value, str):
                if value not in status.get("connected_teams", []):
                    status.setdefault("connected_teams", []).append(value)
            # Als value een lijst is (volledige overschrijving), vervang
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

# --- Interface ---
st.sidebar.title("Instellingen")
role = st.sidebar.radio("Kies je rol:", ["Team", "Host"])

if role == "Host":
    st.title("Admin Panel - Foto Blokjes Quiz")
    status = get_status()

    # --- TEAM BEHEER SECTIE ---
    with st.expander("👥 Team Beheer (Inloggen/Uitloggen)", expanded=False):
        teams = status.get("connected_teams", [])
        if teams:
            st.write(f"Huidige teams: {', '.join(teams)}")
            
            # Selectiebox om één team te verwijderen
            team_to_remove = st.selectbox("Selecteer een team om te verwijderen:", [""] + teams)
            if st.button("Verwijder geselecteerd team") and team_to_remove:
                new_teams = [t for t in teams if t != team_to_remove]
                update_db(connected_teams=new_teams)
                st.rerun()
            
            # Knop voor volledige reset
            if st.button("🔥 Wis ALLE teams"):
                update_db(connected_teams=[])
                st.rerun()
        else:
            st.write("*Geen teams verbonden.*")

    with st.sidebar:
        st.header("Spelinstellingen")
        current_subject = st.text_input("Onderwerp van de ronde:", value=status.get("subject", ""))
        if st.button("Update Onderwerp"):
            update_db(subject=current_subject)
            
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

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("▶️ Start / Reset Ronde"):
                order = list(range(total_cells))
                random.shuffle(order)
                update_db(winner=None, active=True, revealed=[], order=order, excluded_teams=[])
                st.rerun()
        
        with col2:
            if st.button("❌ Fout! (Uitsluiten)"):
                if status.get("winner"):
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

        if status.get("subject"):
            st.markdown(f"### 💡 Categorie: {status['subject']}")

        placeholder = st.empty()

        if status.get("active") and status.get("winner") is None:
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
            temp_img = np.zeros_like(img_array)
            for idx in status.get("revealed", []):
                r, c = divmod(idx, grid_size)
                temp_img[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w] = \
                    img_array[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
            placeholder.image(temp_img if status.get("revealed") else img_array * 0, use_container_width=True)
            
            if status.get("winner"):
                st.header(f"🏆 {status['winner']} mag antwoorden!")

else:
    # --- TEAM INTERFACE ---
    st.title("Team Buzzer")
    
    # Gebruik een session_state om de teamnaam lokaal vast te houden
    if "my_team_name" not in st.session_state:
        st.session_state.my_team_name = ""

    team_name_input = st.text_input("Teamnaam:", value=st.session_state.my_team_name, placeholder="Voer je naam in...")
    
    if team_name_input:
        st.session_state.my_team_name = team_name_input
        update_db(connected_teams=team_name_input)
        
        status = get_status()
        
        # Check of de host dit team heeft verwijderd
        if team_name_input not in status.get("connected_teams", []):
            st.warning("Je bent niet meer aangemeld. Vul je naam opnieuw in.")
            st.session_state.my_team_name = ""
            st.rerun()

        excluded_teams = status.get("excluded_teams", [])
        if status.get("subject"):
            st.info(f"Categorie: {status['subject']}")

        if team_name_input in excluded_teams:
            st.error("❌ Fout antwoord. Wacht op de volgende foto.")
        elif not status.get("active"):
            st.info("Wacht op de Host...")
        elif status.get("winner"):
            if status["winner"] == team_name_input:
                st.success("JULLIE ZIJN EERST!")
            else:
                st.warning(f"{status['winner']} antwoordt...")
        else:
            if st.button("🚨 IK WEET HET! 🚨", use_container_width=True):
                s = get_status()
                if s.get("winner") is None and team_name_input not in s.get("excluded_teams", []):
                    update_db(winner=team_name_input)
                st.rerun()
        
        time.sleep(1)
        st.rerun()
