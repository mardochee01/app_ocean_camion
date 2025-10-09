# ===============================
# 🚚 Application Suivi des Tournées de Camions
# ===============================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client
import os
import json

# =========================
# ⚙️ CONFIGURATION GLOBALE
# =========================
st.set_page_config(page_title="Suivi Camions", layout="centered")

# ⚙️ Connexion Supabase (via st.secrets)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))

@st.cache_resource
def init_supabase():
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
        max-width: 750px;
    }
    h1, h2, h3 { text-align: center; }
    .stButton button {
        width: 100%;
        background-color: #009999;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.6rem;
    }
    .validated {
        color: green;
        font-weight: bold;
    }
    .pending {
        color: gray;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# 🧭 MENU LATÉRAL
# =========================
menu = st.sidebar.radio("📂 Menu", ["🧾 Enregistrement", "📊 Consultation"])

# =========================
# 🔹 PAGE 1 : ENREGISTREMENT PROGRESSIF
# =========================
if menu == "🧾 Enregistrement":
    st.title("🧾 Enregistrement des camions")

    # Dictionnaire des usines par ville
    usines_dict = {
        "Abidjan": [
            "CEMOI AFRICA.S", "TRANSIT INT", "CENTRAL.T", "OLAM", "ECOOKIM",
            "COEX.CI", "SICOCOA", "TOUTON", "SUTEC", "AWAZEN",
            "ZAMACOM", "CARGILL", "SUV", "S3C", "SUCDEN", "CAP SACO"
        ],
        "San Pedro": [
            "CEMOI AFRICA", "SOUR", "SITAPA", "SACC", "OLAM",
            "ICP", "SNCI", "CGB", "SACO", "ECOOKIM",
            "SUCDEN", "CARGILL", "S3C", "CENTRALE IND",
            "KINEDEN", "CACL", "TOUTON", "AWAHUS", "ZAMACOM", "SUV"
        ]
    }

    # Sélection de la ville
    ville = st.selectbox("📍 Sélectionnez une ville :", ["Abidjan", "San Pedro"])

    # Initialisation session
    if "tournee_data" not in st.session_state:
        st.session_state.tournee_data = {}
        st.session_state.selected_usine = None

    # Liste des usines
    usines = usines_dict.get(ville, [])
    usine_status = st.session_state.tournee_data.get(ville, {})

    # Sélection d’une usine
    usine_select = st.selectbox(
        "🏭 Choisissez une usine :", usines,
        index=0,
        key="usine_selection",
        
        
    )
    st.session_state.selected_usine = usine_select

    # Affichage du statut
    status = "✅ Validé" if usine_select in usine_status else "🕓 En attente"
    st.markdown(f"**Statut :** {'<span class=\"validated\">✅ Validé</span>' if usine_select in usine_status else '<span class=\"pending\">🕓 En attente</span>'}", unsafe_allow_html=True)

    # Nombre de camions
    current_value = usine_status.get(usine_select, 0)
    nombre = st.number_input("🚛 Nombre de camions :", min_value=0, step=1, value=current_value, key="nb_camions")

    # Validation / mise à jour
    if st.button("✅ Valider cette usine"):
        if ville not in st.session_state.tournee_data:
            st.session_state.tournee_data[ville] = {}
        st.session_state.tournee_data[ville][usine_select] = nombre
        st.success(f"Usine {usine_select} enregistrée ({nombre} camions).")

    # Tableau récapitulatif
    st.markdown("### 📋 Récapitulatif")
    if ville in st.session_state.tournee_data and st.session_state.tournee_data[ville]:
        recap = pd.DataFrame(
            list(st.session_state.tournee_data[ville].items()),
            columns=["Usine", "Camions"]
        )
        st.table(recap)
    else:
        st.info("Aucune usine encore enregistrée pour cette ville.")

    # Enregistrement global
    if st.button("💾 Enregistrer la tournée complète"):
        if ville not in st.session_state.tournee_data or not st.session_state.tournee_data[ville]:
            st.warning("Veuillez saisir au moins une usine avant d’enregistrer.")
        else:
            data = {
                "date": datetime.now().isoformat(),
                "ville": ville,
                "usines": st.session_state.tournee_data[ville],
                "total": sum(st.session_state.tournee_data[ville].values())
            }
            try:
                supabase.table("tournees").insert(data).execute()
                st.success(f"Tournée enregistrée avec succès ({data['total']} camions à {ville}).")
                del st.session_state.tournee_data[ville]  # Nettoyage
            except Exception as e:
                st.error(f"Erreur d’enregistrement : {e}")

# =========================
# 🔹 PAGE 2 : CONSULTATION + ENVOI
# =========================
if menu == "📊 Consultation":
    st.title("📊 Récapitulatif journalier")

    # --- Charger toutes les tournées ---
    @st.cache_data(ttl=120)
    def load_tournees():
        try:
            data = supabase.table("tournees").select("*").execute()
            return data.data
        except Exception as e:
            st.error(f"Erreur de chargement : {e}")
            return []

    records = load_tournees()
    if not records:
        st.info("Aucune donnée enregistrée.")
        st.stop()

    # --- Nettoyage ---
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["jour"] = df["date"].dt.date

    # --- Filtres dynamiques ---
    st.subheader("🎚️ Filtres de consultation")
    col1, col2, col3 = st.columns(3)
    villes = ["Toutes"] + sorted(df["ville"].unique())
    selected_ville = col1.selectbox("Ville :", villes)

    usines_all = sorted({u for sublist in df["usines"].apply(lambda x: json.loads(x) if isinstance(x, str) else x) for u in sublist})
    usines = ["Toutes"] + usines_all
    selected_usine = col2.selectbox("Usine :", usines)

    date_debut = col3.date_input("📅 Début :", datetime.now().date() - timedelta(days=7))
    date_fin = col3.date_input("📅 Fin :", datetime.now().date())

    # --- Application des filtres ---
    mask = (df["jour"] >= date_debut) & (df["jour"] <= date_fin)
    if selected_ville != "Toutes":
        mask &= (df["ville"] == selected_ville)
    df_filtered = df[mask]

    # --- Transformation des données ---
    details = []
    for _, row in df_filtered.iterrows():
        usines = json.loads(row["usines"]) if isinstance(row["usines"], str) else row["usines"]
        for usine, qte in usines.items():
            details.append({"jour": row["jour"], "ville": row["ville"], "usine": usine, "camions": qte})
    df_long = pd.DataFrame(details)

    if selected_usine != "Toutes":
        df_long = df_long[df_long["usine"] == selected_usine]

    # --- Récapitulatif global par ville ---
    st.markdown("### 🏙️ Récapitulatif journalier par ville")
    recap_ville = df_long.groupby(["jour", "ville"], as_index=False)["camions"].sum()
    st.dataframe(recap_ville, use_container_width=True)

    # --- Sélection d'une ville pour détail ---
    st.markdown("### 🏭 Détails par usine")
    villes_dispo = recap_ville["ville"].unique()
    ville_click = st.selectbox("Choisissez une ville à détailler :", villes_dispo)
    df_detail = df_long[df_long["ville"] == ville_click].groupby(["usine"], as_index=False)["camions"].sum()

    st.table(df_detail)

    # --- Statistiques globales ---
    total_camions = df_long["camions"].sum()
    nb_usines = df_long["usine"].nunique()
    nb_villes = df_long["ville"].nunique()
    st.markdown("---")
    st.markdown(f"""
    ### 📈 Statistiques globales
    - 🏙️ **{nb_villes} villes**
    - 🏭 **{nb_usines} usines concernées**
    - 🚛 **{total_camions} camions enregistrés**
    """)