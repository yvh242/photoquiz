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
    # Probeer het bestand te lezen, probeer opnieuw bij een fout (bezet bestand)
    for _ in range(5):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            time.sleep(0.1)
    return {}

def update_db(**kwargs):
    status = get_status()
    if not status: return # Veiligheid bij leesfout
    
    for key, value in kwargs.items():
        if key == "connected_teams":
            if value not in status.get("connected_teams", []):
                status.setdefault("connected_teams", []).append(value)
        else:
            status[key] = value
            
    # Veilig schrijven: schrijf eerst naar tijdelijk bestand en hernoem (voorkomt corruptie)
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

    with st.sidebar:
        st.header("Spelinstellingen")
        current_subject = st.text_input("Onderwerp van de ronde:", value=status.get("subject", ""))
        if st.button("Update Onderwerp"):
            update_db(subject=current_subject)
            
        grid_size = st.slider("Raster grootte", 4, 30, 10)
        delay = st.slider("Snelheid (sec)", 0.05, 2.0, 0.4)
        uploaded_files = st.file_uploader("Upload foto's", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    st.subheader("👥 Ingelogde Teams")
    teams = status.get("connected_teams", [])
    st.write(", ".join(teams) if teams else "*Nog geen teams verbonden...*")

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
            
            # Animatie loop
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
    st.title("Team Buzzer")
    team_name = st.text_input("Teamnaam:", placeholder="Voer je naam in...")
    
    if team_name:
        update_db(connected_teams=team_name)
        status = get_status()
        excluded_teams = status.get("excluded_teams", [])

        if status.get("subject"):
            st.info(f"Categorie: {status['subject']}")

        if team_name in excluded_teams:
            st.error("❌ Fout antwoord gegeven. Wacht op de volgende foto.")
        elif not status.get("active"):
            st.info("Wacht tot de Host de ronde start...")
        elif status.get("winner"):
            if status["winner"] == team_name:
                st.success("JULLIE ZIJN EERST!")
            else:
                st.warning(f"{status['winner']} antwoordt...")
        else:
            if st.button("🚨 IK WEET HET! 🚨", use_container_width=True):
                s = get_status()
                if s.get("winner") is None and team_name not in s.get("excluded_teams", []):
                    update_db(winner=team_name)
                st.rerun()
        
        time.sleep(1)
        st.rerun()
