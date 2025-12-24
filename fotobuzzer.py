import streamlit as st
import PIL.Image as Image
import numpy as np
import random
import time
import json
import os

# --- 1. DATABASE LOGICA (STABIEL) ---
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
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"connected_teams": [], "revealed": [], "excluded_teams": []}

def update_db(**kwargs):
    status = get_status()
    for key, value in kwargs.items():
        if key == "connected_teams":
            if value not in status.get("connected_teams", []):
                status.setdefault("connected_teams", []).append(value)
        else:
            status[key] = value
    with open(DB_FILE, "w") as f:
        json.dump(status, f)

init_db()

# --- 2. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Quiz Controle")
    role = st.radio("Kies rol:", ["Host", "Team"])
    
    if role == "Host":
        st.divider()
        # Belangrijkste knoppen bovenaan
        if st.button("▶️ START RONDE", use_container_width=True):
            status = get_status()
            gs = st.session_state.get('gs_val', 10)
            order = list(range(gs * gs))
            random.shuffle(order)
            update_db(winner=None, active=True, revealed=[], order=order, excluded_teams=[], game_started=True, show_all=False)
            st.rerun()

        if st.button("👁️ ONTHUL ALLES", use_container_width=True):
            update_db(show_all=True, active=False)
            st.rerun()

        if st.button("⏭️ VOLGENDE FOTO", use_container_width=True):
            if 'photo_idx' not in st.session_state: st.session_state.photo_idx = 0
            st.session_state.photo_idx += 1
            update_db(winner=None, active=False, revealed=[], order=[], game_started=False, show_all=False)
            st.rerun()

        st.divider()
        uploaded_files = st.file_uploader("Upload foto's", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        grid_size = st.slider("Raster grootte", 4, 30, 10, key="gs_val")
        delay = st.slider("Snelheid", 0.05, 1.0, 0.3)
        
        st.divider()
        if st.button("🔄 Ververs Teams"): st.rerun()
        status = get_status()
        st.write("**Teams:**")
        for t in status.get("connected_teams", []):
            label = "🚫" if t in status.get("excluded_teams", []) else "✅"
            st.write(f"{label} {t}")
        
        if st.button("🔥 RESET ALLES"):
            init_db(force=True)
            st.rerun()

# --- 3. HOOFDSCHERM HOST ---
if role == "Host":
    status = get_status()
    st.title("📸 Foto Quiz")
    
    # Categorie beheer
    c_sub1, c_sub2 = st.columns([3,1])
    with c_sub1:
        subj = st.text_input("Categorie:", value=status.get("subject", ""), label_visibility="collapsed")
    with c_sub2:
        if st.button("Opslaan"): update_db(subject=subj); st.rerun()

    if status.get("subject"):
        st.markdown(f"<h1 style='text-align:center; color:red;'>{status['subject']}</h1>", unsafe_allow_html=True)

    if uploaded_files:
        idx = st.session_state.get('photo_idx', 0) % len(uploaded_files)
        img = Image.open(uploaded_files[idx]).convert("RGB")
        img_array = np.array(img)
        h, w, _ = img_array.shape
        ch, cw = h // grid_size, w // grid_size
        
        # Fout knop (midden van scherm)
        if status.get("winner"):
            if st.button(f"❌ {status['winner']} IS FOUT", use_container_width=True):
                excl = status.get("excluded_teams", [])
                if status["winner"] not in excl: excl.append(status["winner"])
                update_db(winner=None, active=True, excluded_teams=excl)
                st.rerun()

        ph = st.empty()

        if status.get("show_all"):
            ph.image(img_array, use_container_width=True)
        elif status.get("game_started") and status.get("active") and not status.get("winner"):
            rev = status.get("revealed", [])
            order = status.get("order", [])
            for i in range(len(rev), len(order)):
                cur = get_status()
                if cur.get("winner") or cur.get("show_all"): st.rerun()
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
                ph.image(img_array * 0, caption="Klik op START in zijbalk", use_container_width=True)
            else:
                ph.image(temp, use_container_width=True)
            
            if status.get("winner"):
                st.success(f"🏆 {status['winner']} mag antwoorden!")

# --- 4. TEAM INTERFACE ---
else:
    st.title("🚨 Buzzer")
    my_name = st.text_input("Naam:")
    if my_name:
        update_db(connected_teams=my_name)
        status = get_status()
        
        if status.get("subject"): st.info(f"Categorie: {status['subject']}")
        
        if my_name in status.get("excluded_teams", []):
            st.error("Je bent uitgesloten.")
        elif status.get("winner"):
            st.warning(f"{status['winner']} heeft gebuzzert!")
        elif not status.get("game_started"):
            st.info("Wachten op start...")
        else:
            if st.button("🚨 BUZZER 🚨", use_container_width=True):
                s = get_status()
                if not s.get("winner"):
                    update_db(winner=my_name)
                st.rerun()
        time.sleep(1)
        st.rerun()
