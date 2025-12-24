import streamlit as st
import PIL.Image as Image
import numpy as np
import random
import time
import json
import os

# --- DATABASE LOGICA ---
DB_FILE = "quiz_state.json"

def init_db(force=False):
    if not os.path.exists(DB_FILE) or force:
        data = {
            "winner": None, "active": False, "revealed": [], "order": [], 
            "excluded_teams": [], "connected_teams": [], "subject": "",
            "game_started": False, "show_all": False
        }
        with open(DB_FILE, "w") as f:
            json.dump(data, f)

def get_status():
    for _ in range(5):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
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
    with open(DB_FILE, "w") as f:
        json.dump(status, f)

init_db()

# --- SIDEBAR (Alleen voor instellingen en Team-overzicht) ---
with st.sidebar:
    st.title("⚙️ Instellingen")
    role = st.radio("Kies rol:", ["Team", "Host"])
    
    if role == "Host":
        st.divider()
        uploaded_files = st.file_uploader("1. Upload foto's", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="uploader")
        grid_size = st.slider("2. Raster grootte", 4, 30, 10)
        delay = st.slider("3. Snelheid", 0.05, 1.0, 0.3)
        
        st.divider()
        st.subheader("👥 Teams")
        if st.button("🔄 Ververs Teamlijst"): # DE NIEUWE REFRESH KNOP
            st.rerun()
            
        status = get_status()
        teams = status.get("connected_teams", [])
        for t in teams:
            icon = "🚫" if t in status.get("excluded_teams", []) else "✅"
            st.write(f"{icon} {t}")
        
        if st.button("🔥 VOLLEDIGE RESET"):
            init_db(force=True)
            st.rerun()

# --- HOOFDSCHERM (HOST) ---
if role == "Host":
    status = get_status()
    st.title("📸 Foto Blokjes Quiz")
    
    # Categorie invoer en weergave
    col_cat1, col_cat2 = st.columns([3, 1])
    with col_cat1:
        new_subj = st.text_input("Onderwerp:", value=status.get("subject", ""), label_visibility="collapsed", placeholder="Typ hier de categorie...")
    with col_cat2:
        if st.button("Zet Categorie"):
            update_db(subject=new_subj)
            st.rerun()

    if status.get("subject"):
        st.markdown(f"<h1 style='text-align: center; color: red;'>{status['subject']}</h1>", unsafe_allow_html=True)

    if uploaded_files:
        # --- ACTIE KNOPPEN BOVEN DE FOTO ---
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("▶️ START RONDE", use_container_width=True):
                total_cells = grid_size * grid_size
                order = list(range(total_cells))
                random.shuffle(order)
                update_db(winner=None, active=True, revealed=[], order=order, excluded_teams=[], game_started=True, show_all=False)
                st.rerun()
        with c2:
            if st.button("👁️ ONTHUL ALLES", use_container_width=True):
                update_db(show_all=True, active=False)
                st.rerun()
        with c3:
            if st.button("⏭️ VOLGENDE", use_container_width=True):
                st.session_state.photo_idx = (st.session_state.get('photo_idx', 0) + 1) % len(uploaded_files)
                update_db(winner=None, active=False, revealed=[], order=[], excluded_teams=[], game_started=False, show_all=False)
                st.rerun()

        # Fout-knop (Groot in het midden als er iemand buzzed)
        if status.get("winner"):
            st.error(f"Heeft {status['winner']} het fout?")
            if st.button(f"❌ JA, {status['winner']} IS FOUT", use_container_width=True):
                excl = status.get("excluded_teams", [])
                if status["winner"] not in excl: excl.append(status["winner"])
                update_db(winner=None, active=True, excluded_teams=excl)
                st.rerun()

        # --- FOTO DISPLAY ---
        idx = st.session_state.get('photo_idx', 0)
        if idx >= len(uploaded_files): idx = 0
        img = Image.open(uploaded_files[idx]).convert("RGB")
        img_array = np.array(img)
        h, w, _ = img_array.shape
        ch, cw = h // grid_size, w // grid_size
        
        ph = st.empty()

        if status.get("show_all"):
            ph.image(img_array, use_container_width=True)
        elif status.get("game_started") and status.get("active") and status.get("winner") is None:
            rev = status.get("revealed", [])
            order = status.get("order", [])
            for i in range(len(rev), len(order)):
                cur = get_status()
                if cur.get("winner") or cur.get("show_all") or not cur.get("game_started"):
                    st.rerun()
                rev.append(order[i])
                update_db(revealed=rev)
                temp = np.zeros_like(img_array)
                for cell in rev:
                    r, c = divmod(cell, grid_size)
                    temp[r*ch:(r+1)*ch, c*cw:(c+1)*cw] = img_array[r*ch:(r+1)*ch, c*cw:(c+1)*cw]
                ph.image(temp, use_container_width=True)
                time.sleep(delay)
        else:
            temp = np.zeros_like(img_array)
            for cell in status.get("revealed", []):
                r, c = divmod(cell, grid_size)
                temp[r*ch:(r+1)*ch, c*cw:(c+1)*cw] = img_array[r*ch:(r+1)*ch, c*cw:(c+1)*cw]
            
            if not status.get("game_started") and not status.get("show_all"):
                ph.image(img_array * 0, caption="Klik op START", use_container_width=True)
            else:
                ph.image(temp, use_container_width=True)
            
            if status.get("winner"):
                st.success(f"🏆 {status['winner']} IS AAN DE BEURT!")
    else:
        st.info("Upload eerst foto's in de zijbalk.")

# --- TEAM INTERFACE ---
else:
    st.title("🚨 Team Buzzer")
    name = st.text_input("Naam:", value=st.session_state.get("my_name", ""))
    if name:
        st.session_state.my_name = name
        update_db(connected_teams=name)
        status = get_status()
        
        if name not in status.get("connected_teams", []):
            st.session_state.my_name = ""
            st.rerun()

        if status.get("subject"): st.info(f"Categorie: {status['subject']}")
        
        if name in status.get("excluded_teams", []):
            st.error("Wacht op de volgende foto...")
        elif not status.get("game_started"):
            st.info("Wachten op de host...")
        elif status.get("winner"):
            st.success("Er wordt geantwoord...")
        else:
            if st.button("🚨 IK WEET HET! 🚨", use_container_width=True):
                update_db(winner=name)
                st.rerun()
        time.sleep(1)
        st.rerun()
