# ===============================
# 🚚 Application Suivi des Tournées de Camions
# ===============================

import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
import os
import json
import io
from openpyxl import Workbook

# =========================
# ⚙️ CONFIGURATION GLOBALE
# =========================
st.set_page_config(page_title="Suivi Camions", layout="centered")

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
    
    .stButton, .stDownloadButton {
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
    
    .stDownloadButton > button {
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
# 🧭 MENU LATÉRAL
# =========================
menu = st.sidebar.radio("📂 Menu", [
    "🧾 Enregistrement",
    "📊 Récapitulatif journalier",
    "📈 Filtres et export"
])

# =========================
# 🔹 PAGE 1 : ENREGISTREMENT
# =========================
if menu == "🧾 Enregistrement":
    st.title("🧾 Enregistrement des camions")

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

    ville = st.selectbox("📍 Ville :", ["Abidjan", "San Pedro"])
    usines = usines_dict.get(ville, [])
    usine_select = st.selectbox("🏭 Choisissez une usine :", usines)

    # Utilisation d'une clé fixe avec valeur par défaut
    current_value = st.session_state.tournee_data.get(ville, {}).get(usine_select, 0)
    nombre = st.number_input(
        "🚛 Nombre de camions :", 
        min_value=0, 
        step=1, 
        value=current_value,
        key=f"camions_{ville}_{usine_select}"
    )

    # Enregistrement temporaire
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("✅ Valider cette usine", key="btn_valider"):
            if ville not in st.session_state.tournee_data:
                st.session_state.tournee_data[ville] = {}
            st.session_state.tournee_data[ville][usine_select] = nombre
            st.success(f"✅ {usine_select} : {nombre} camions")
    
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
        st.dataframe(recap, use_container_width=True)
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

# =========================
# 🔹 PAGE 2 : RÉCAP JOURNALIER
# =========================
elif menu == "📊 Récapitulatif journalier":
    st.title("📊 Récapitulatif journalier")

    @st.cache_data(ttl=120)
    def load_tournees():
        try:
            return supabase.table("tournees").select("*").execute().data
        except Exception as e:
            st.error(f"Erreur de chargement : {e}")
            return []

    data = load_tournees()
    if not data:
        st.info("Aucune donnée disponible.")
        st.stop()

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["jour"] = df["date"].dt.date
    today = datetime.now().date()
    df = df[df["jour"] == today]

    if df.empty:
        st.warning("Aucune donnée enregistrée pour aujourd'hui.")
        st.stop()

    # Transformation longue
    details = []
    for _, row in df.iterrows():
        usines = json.loads(row["usines"]) if isinstance(row["usines"], str) else row["usines"]
        for usine, n in usines.items():
            details.append({"ville": row["ville"], "usine": usine, "camions": n})

    df_long = pd.DataFrame(details)

    # Totaux
    st.markdown("### 🏙️ Totaux journaliers par ville")
    recap_ville = df_long.groupby("ville", as_index=False)["camions"].sum()
    st.dataframe(recap_ville, use_container_width=True)

    # Détails
    st.markdown("### 🏭 Détails par usine")
    ville_choice = st.selectbox("Choisissez la ville :", sorted(df_long["ville"].unique()))
    st.dataframe(df_long[df_long["ville"] == ville_choice], use_container_width=True)

# =========================
# 🔹 PAGE 3 : FILTRES + EXPORT
# =========================
elif menu == "📈 Filtres et export":
    st.title("📈 Analyse et Export des données")

    @st.cache_data(ttl=300)
    def load_all():
        try:
            return supabase.table("tournees").select("*").execute().data
        except Exception as e:
            st.error(f"Erreur : {e}")
            return []

    data = load_all()
    if not data:
        st.info("Aucune donnée disponible.")
        st.stop()

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["jour"] = df["date"].dt.date

    # Filtres
    villes = ["Toutes"] + sorted(df["ville"].unique())
    ville = st.selectbox("📍 Ville :", villes)

    usines_all = sorted({
        u for sub in df["usines"].apply(lambda x: json.loads(x) if isinstance(x, str) else x) for u in sub
    })

    usines_selection = st.multiselect("🏭 Sélectionnez les usines :", usines_all, default=usines_all)
    date_debut = st.date_input("📅 Début :", df["jour"].min())
    date_fin = st.date_input("📅 Fin :", df["jour"].max())

    # Application des filtres
    mask = (df["jour"] >= date_debut) & (df["jour"] <= date_fin)
    if ville != "Toutes":
        mask &= (df["ville"] == ville)
    df_filtered = df[mask]

    # Transformation
    details = []
    for _, row in df_filtered.iterrows():
        usines = json.loads(row["usines"]) if isinstance(row["usines"], str) else row["usines"]
        for u, q in usines.items():
            if u in usines_selection:
                details.append({"jour": row["jour"], "ville": row["ville"], "usine": u, "camions": q})

    df_long = pd.DataFrame(details)

    # Affichage
    if not df_long.empty and "ville" in df_long.columns:
        recap_ville = df_long.groupby("ville", as_index=False)["camions"].sum()
        st.dataframe(recap_ville, use_container_width=True)
    else:
        st.warning("⚠️ Aucune donnée à afficher. Vérifiez vos filtres.")

    st.markdown("### 🏭 Détails par usine")

    if not df_long.empty and all(col in df_long.columns for col in ["ville", "usine", "camions"]):
        recap_usine = df_long.groupby(["ville", "usine"], as_index=False)["camions"].sum()
        st.dataframe(recap_usine, use_container_width=True)
    else:
        st.info("Aucun détail disponible pour les critères choisis.")

    # Export complet
    st.markdown("---")
    st.subheader("📦 Télécharger la base de données complète")

    @st.cache_data(ttl=300)
    def load_all_data():
        try:
            data = supabase.table("tournees").select("*").execute()
            return pd.DataFrame(data.data)
        except Exception as e:
            st.error(f"Erreur lors du chargement : {e}")
            return pd.DataFrame()

    df_all = load_all_data()

    if not df_all.empty:
        df_all["usines"] = df_all["usines"].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)
        if "date" in df_all.columns:
            df_all["date"] = pd.to_datetime(df_all["date"], errors="coerce").dt.tz_localize(None)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_all.to_excel(writer, index=False, sheet_name="Tournées_Complètes")

        st.download_button(
            label="📤 Télécharger toutes les données (Excel)",
            data=buffer.getvalue(),
            file_name=f"base_tournees_completes_{datetime.now().date()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("⚠️ Aucune donnée disponible dans la base Supabase.")