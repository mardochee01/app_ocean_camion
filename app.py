# ===============================
# 🚚 Application Suivi des Tournées de Camions
# ===============================

import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
import os
import json
#import win32com.client as win32
#import pythoncom
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =========================
# ⚙️ CONFIGURATION GLOBALE
# =========================
st.set_page_config(page_title="Suivi Camions", layout="centered")

# Utiliser st.secrets sur Cloud (au lieu de .env ; ajoutez SUPABASE_URL et SUPABASE_KEY dans Settings > Secrets)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))

# Connexion à Supabase (cachée comme ressource, OK pour connexions persistantes)
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# Flag session pour clé de cache dynamique (force refresh après insert)
if 'refresh_key' not in st.session_state:
    st.session_state.refresh_key = datetime.now().isoformat()

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
    ville = st.selectbox("📍 Ville", options=ville_options, index=0, key="ville_select")

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
                st.cache_data.clear()  # Efface TOUS les caches data (force re-fetch sur page 2)
                st.session_state.refresh_key = datetime.now().isoformat()  # Met à jour la clé pour invalidation future
                st.success(f"Tournée enregistrée avec succès ({total} camions à {ville})")
                st.rerun()  # Force re-run global pour refresh immédiat (utile si on reste sur page 1)
            except Exception as e:
                st.error(f"Erreur d’enregistrement : {e}")

# =======================================================
# 📊 PAGE 2 : CONSULTATION & ENVOI MAIL
# =======================================================
elif menu == "📊 Consultation & envoi":
    st.title("📊 Récapitulatif du jour")

    today = datetime.now().date().isoformat()
    
    # Cache avec TTL=60s (1 min auto-refresh) ET clé dynamique (refresh_key) pour invalidation après insert
    @st.cache_data(ttl=60)
    def load_tournees(today, refresh_key):
        try:
            data = (
                supabase.table("tournees")
                .select("*")
                .gte("date", today)
                .order("date", desc=True)
                .execute()
            )
            return data.data
        except Exception as e:
            st.error(f"Erreur de chargement des données : {e}")
            return []

    records = load_tournees(today, st.session_state.refresh_key)  # Inclut refresh_key pour casser le cache après insert

    if records:
        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["heure"] = df["date"].dt.strftime("%H:%M")

        st.subheader("🗓️ Tournées enregistrées aujourd’hui")
        st.dataframe(df[["heure", "ville", "total"]], use_container_width=True)

        # Sélection d’une tournée
        st.markdown("---")
        st.subheader("🔍 Détail d’une tournée")
        
        def format_tournee(i):
            return f"{df.loc[i, 'ville']} – {df.loc[i, 'heure']} ({df.loc[i, 'total']} camions)"
        
        selection = st.selectbox(
            "Choisissez une tournée à consulter :",
            df.index,
            format_func=format_tournee,
            key="tournee_select"
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
            "Destinataires :", direction_mails, default=[direction_mails[0]],
            key="destinataires_multi"
        )

        # Ancien code Outlook commenté
        #if st.button("✉️ Envoyer ce résumé par mail"):
        #   try:
        #      pythoncom.CoInitialize()
#
#               html_body = f"""
#              <html>
#             <body style="font-family:Arial;">
#                <h2 style="color:#00796B;">Résumé de la tournée du {selected['ville']} ({selected['heure']})</h2>
#               <p><b>Date :</b> {selected['date'].strftime('%d/%m/%Y à %H:%M')}</p>
#              <p><b>Total camions :</b> {selected['total']}</p>
#             <table border="1" cellspacing="0" cellpadding="5" 
#                style="border-collapse:collapse; width:70%;" class="table-style">
#               <tr><th>Usine</th><th>Nombre de camions</th></tr>
#              {usine_table}
#         </table>
#            <br>
#           <p>Envoyé automatiquement depuis l’application <b>Suivi Camions</b>.</p>
#      </body>
#     </html>
#        """
#
#         outlook = win32.Dispatch("Outlook.Application")
#        mail = outlook.CreateItem(0)
#       mail.To = "; ".join(to_emails)
#      mail.Subject = f"Tournée {selected['ville']} – {selected['date'].strftime('%d/%m/%Y %H:%M')}"
#     mail.HTMLBody = html_body
#    mail.Send()  # Envoie le mail directement
#
#       pythoncom.CoUninitialize()
#
#       st.success("📧 Mail envoyé avec succès !")
##          except Exception as e:
#            st.error(f"Erreur lors de l’envoi : {e}")
#           if 'pythoncom' in locals():
#              pythoncom.CoUninitialize()

        # Nouveau code SMTP
        if st.button("✉️ Envoyer ce résumé par mail", key="send_email_btn"):
            try:
                # Config SMTP (adapte à ton provider ; ex. Gmail ou Outlook.com)
                smtp_server = "smtp.gmail.com"  # Ou "smtp-mail.outlook.com" pour Hotmail/Outlook
                smtp_port = 587
                sender_email = "ton-email@exemple.com"  # Ton email expéditeur
                sender_password = st.secrets["EMAIL_PASSWORD"]  # Stocke le mot de passe en secret (voir étape 3)

                # Destinataires
                to_emails_str = ", ".join(to_emails)  # Note : virgule pour SMTP

                # Corps HTML (identique à l'ancien)
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
                    <p>Envoyé automatiquement depuis l’app <b>Suivi Camions</b>.</p>
                </body>
                </html>
                """

                # Créer le message
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"Tournée {selected['ville']} – {selected['date'].strftime('%d/%m/%Y %H:%M')}"
                msg['From'] = sender_email
                msg['To'] = to_emails_str

                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

                # Envoi SMTP
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()  # Chiffrement
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, to_emails, msg.as_string())  # Note : liste pour multiples destinataires
                server.quit()

                st.success("📧 Mail envoyé avec succès !")
            except Exception as e:
                st.error(f"Erreur lors de l’envoi : {e}")
    else:
        st.info("Aucune tournée enregistrée aujourd’hui.")