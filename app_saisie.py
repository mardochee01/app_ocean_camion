# ===============================
# 🚛 Application Saisie des Tournées de Camions
# ===============================

import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
import os
import json

# =========================
# ⚙️ CONFIGURATION GLOBALE
# =========================
st.set_page_config(page_title="Saisie des Camions", layout="centered")

SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))

@st.cache_resource
def init_supabase():
    """Initialise la connexion à Supabase."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# =========================
# 🎨 STYLE GLOBAL
# =========================
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 850px;
    }
    h1, h2, h3 { text-align: center; }
    
    .stButton {
        text-align: center;
        margin: 0 auto;
    }
    
    .stButton > button {
        display: inline-block !important;
        background-color: #009999 !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
        width: auto !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# 🔹 PAGE UNIQUE : ENREGISTREMENT
# =========================

st.title("🧾 Saisie des tournées de camions")

# Liste des usines par ville
usines_dict = {
    "Abidjan": [
        "AFRICA SOURCING", "AWAZEN", "CAP", "CARGILL", "CEMOI", "CENTRAL.T", 
        "COEX.CI", "ECOOKIM", "OLAM", "S3C", "SACO", "SICOCOA", 
        "SUCDEN", "SUTEC", "SUV", "TOUTON", "TRANSCAO", "TRANSIT INT", 
        "ZAMACOM"
    ],
    "San Pedro": [
        "AFRICA SOURCING", "AWAHUS", "CACL", "CARGILL", "CEMOI", "CENTRALE IND", 
        "CGB", "CITRAC", "ECOOKIM", "ICP", "IPSC", "KINEDEN", "MEDLOG", 
        "OLAM", "S3C", "SACC", "SACO", "SIMAT 2", "SITAPA", "SNCI", 
        "SOUR", "SUCDEN", "SUV", "TOUTON", "ZAMACOM"
    ]
}

# Initialisation du session_state
if "tournee_data" not in st.session_state:
    st.session_state.tournee_data = {}

# Flag pour afficher le message de succès
if "save_success" not in st.session_state:
    st.session_state.save_success = False

# Afficher le message de succès si présent
if st.session_state.save_success:
    st.success("🎉 Tournée enregistrée avec succès dans la base de données !")
    st.balloons()
    st.session_state.save_success = False

# Sélection ville et usine
ville = st.selectbox("📍 Ville :", ["Abidjan", "San Pedro"])
usines = usines_dict.get(ville, [])
usine_select = st.selectbox("🏭 Choisissez une usine :", usines)

# Nombre de camions
current_value = st.session_state.tournee_data.get(ville, {}).get(usine_select, 0)
nombre = st.number_input(
    "🚛 Nombre de camions :", 
    min_value=0, 
    step=1, 
    value=current_value,
    key=f"camions_{ville}_{usine_select}"
)

# Boutons d'action
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("✅ Valider cette usine", key="btn_valider"):
        if ville not in st.session_state.tournee_data:
            st.session_state.tournee_data[ville] = {}
        st.session_state.tournee_data[ville][usine_select] = nombre
        st.success(f"✅ {usine_select} : {nombre} camions ajoutés")

with col2:
    if st.button("🗑️ Réinitialiser", key="btn_reset"):
        if ville in st.session_state.tournee_data and usine_select in st.session_state.tournee_data[ville]:
            del st.session_state.tournee_data[ville][usine_select]
            st.rerun()

# Récapitulatif temporaire
st.markdown("### 📋 Récapitulatif")
if ville in st.session_state.tournee_data and st.session_state.tournee_data[ville]:
    recap = pd.DataFrame(
        list(st.session_state.tournee_data[ville].items()), 
        columns=["Usine", "Camions"]
    )
    total = recap["Camions"].sum()
    st.dataframe(recap, width="stretch")
    st.metric("Total", f"{total} camions")
else:
    st.info("Aucune usine enregistrée pour cette ville.")

# Enregistrement final vers Supabase
st.markdown("---")
if st.button("💾 Enregistrer la tournée complète", type="primary", key="btn_save"):
    if not st.session_state.tournee_data.get(ville):
        st.warning("⚠️ Aucune usine enregistrée pour cette ville.")
    else:
        data = {
            "date": datetime.now().isoformat(),
            "ville": ville,
            "usines": st.session_state.tournee_data[ville],
            "total": sum(st.session_state.tournee_data[ville].values())
        }
        try:
            supabase.table("tournees").insert(data).execute()
            st.session_state.save_success = True
            del st.session_state.tournee_data[ville]
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erreur lors de l'enregistrement : {e}")
