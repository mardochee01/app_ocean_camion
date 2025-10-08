# ===============================
# 🚚 Application Suivi des Tournées de Camions
# ===============================

import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import os
import json
import win32com.client as win32
import pythoncom

# =========================
# ⚙️ CONFIGURATION GLOBALE
# =========================
st.set_page_config(page_title="Suivi Camions", layout="centered")

# Charger les variables d'environnement
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Connexion à Supabase
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
    h1, h2, h3 {
        text-align: center;
    }
    .stButton button {
        width: 100%;
        background-color: #009999;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.6rem;
    }
    .table-style th {
        background-color: #009999;
        color: white;
        text-align: center;
    }
    .table-style td {
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# 🎛️ MENU LATÉRAL
# =========================
menu = st.sidebar.radio("📂 Menu", ["📝 Saisie des tournées", "📊 Consultation & envoi"])

# =======================================================
# 🧾 PAGE 1 : SAISIE DES TOURNÉES
# =======================================================
if menu == "📝 Saisie des tournées":
    st.title("📝 Enregistrement des tournées de camions")

    # Sélection ville
    ville_options = ["Abidjan", "San Pedro"]
    ville = st.selectbox("📍 Ville", options=ville_options, index=0)

    # Liste des usines
    usines_dict = {
        "Abidjan": [
            "CEMOI AFRICA.S", "TRANSIT INT", "CENTRAL.T", "OLAM", "ECOOKIM", "COEX.CI", "SICOCOA",
            "TOUTON", "SUTEC", "AWAZEN", "ZAMACOM", "CARGILL", "SUV", "S3C", "SUCDEN", "CAP SACO"
        ],
        "San Pedro": [
            "CEMOI AFRICA", "SOUR", "SITAPA", "SACC", "OLAM", "ICP", "SNCI", "CGB", "SACO",
            "ECOOKIM", "SUCDEN", "CARGILL", "S3C", "CENTRALE IND", "KINEDEN", "CACL", "TOUTON",
            "AWAHUS", "ZAMACOM", "SUV"
        ]
    }
    usines = usines_dict.get(ville, [])

    with st.form("form_tournee"):
        st.write(f"### 🏭 Usines à {ville}")
        quantites = {}
        for usine in usines:
            key = f"{ville}_{usine}".replace(" ", "_").lower()
            quantites[usine] = st.number_input(f"Camions pour {usine}", min_value=0, step=1, key=key)

        total = sum(quantites.values())
        submitted = st.form_submit_button("✅ Enregistrer la tournée")

        if submitted:
            data = {
                "date": datetime.now().isoformat(),
                "ville": ville,
                "usines": quantites,
                "total": total
            }
            try:
                supabase.table("tournees").insert(data).execute()
                st.success(f"Tournée enregistrée avec succès ({total} camions à {ville})")
            except Exception as e:
                st.error(f"Erreur d’enregistrement : {e}")

# =======================================================
# 📊 PAGE 2 : CONSULTATION & ENVOI MAIL
# =======================================================
elif menu == "📊 Consultation & envoi":
    st.title("📊 Récapitulatif du jour")

    today = datetime.now().date().isoformat()
    try:
        data = (
            supabase.table("tournees")
            .select("*")
            .gte("date", today)
            .order("date", desc=True)
            .execute()
        )
        records = data.data
    except Exception as e:
        st.error(f"Erreur de chargement des données : {e}")
        records = []

    if records:
        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["heure"] = df["date"].dt.strftime("%H:%M")

        st.subheader("🗓️ Tournées enregistrées aujourd’hui")
        st.dataframe(df[["heure", "ville", "total"]], use_container_width=True)

        # Sélection d’une tournée
        st.markdown("---")
        st.subheader("🔍 Détail d’une tournée")
        selection = st.selectbox(
            "Choisissez une tournée à consulter :",
            df.index,
            format_func=lambda i: f"{df.loc[i, 'ville']} – {df.loc[i, 'heure']} ({df.loc[i, 'total']} camions)"
        )

        selected = df.loc[selection]
        usines = selected["usines"]
        if isinstance(usines, str):
            usines = json.loads(usines)

        # Tableau HTML pour mail
        usine_table = "".join([
            f"<tr><td>{u}</td><td style='text-align:center;'>{q}</td></tr>"
            for u, q in usines.items()
        ])

        st.write(f"**📍 Ville :** {selected['ville']}")
        st.write(f"**🕒 Heure :** {selected['heure']}")
        st.write(f"**🚛 Total camions :** {selected['total']}")
        st.markdown("**🏭 Détails par usine :**")
        st.table(pd.DataFrame(list(usines.items()), columns=["Usine", "Camions"]))

        # Envoi par mail
        st.markdown("---")
        st.subheader("📧 Envoyer à la direction")

        direction_mails = [
            "mardochee.gneran@ocean-ci.com",
            "direction@oceansa.com"
        ]
        to_emails = st.multiselect(
            "Destinataires :", direction_mails, default=[direction_mails[0]]
        )

        if st.button("✉️ Envoyer ce résumé par mail"):
            try:
                pythoncom.CoInitialize()

                html_body = f"""
                <html>
                <body style="font-family:Arial;">
                    <h2 style="color:#00796B;">Résumé de la tournée du {selected['ville']} ({selected['heure']})</h2>
                    <p><b>Date :</b> {selected['date'].strftime('%d/%m/%Y à %H:%M')}</p>
                    <p><b>Total camions :</b> {selected['total']}</p>
                    <table border="1" cellspacing="0" cellpadding="5" 
                        style="border-collapse:collapse; width:70%;" class="table-style">
                        <tr><th>Usine</th><th>Nombre de camions</th></tr>
                        {usine_table}
                    </table>
                    <br>
                    <p>Envoyé automatiquement depuis l’application <b>Suivi Camions</b>.</p>
                </body>
                </html>
                """

                outlook = win32.Dispatch("Outlook.Application")
                mail = outlook.CreateItem(0)
                mail.To = "; ".join(to_emails)
                mail.Subject = f"Tournée {selected['ville']} – {selected['date'].strftime('%d/%m/%Y %H:%M')}"
                mail.HTMLBody = html_body
                mail.Send()  # Envoie le mail directement

                pythoncom.CoUninitialize()

                st.success("📧 Mail envoyé avec succès !")
            except Exception as e:
                st.error(f"Erreur lors de l’envoi : {e}")
                if 'pythoncom' in locals():
                    pythoncom.CoUninitialize()
    else:
        st.info("Aucune tournée enregistrée aujourd’hui.")