import streamlit as st
from PIL import Image, ImageDraw
from gtts import gTTS
import datetime
import pandas as pd
import os
import base64
import tempfile
import smtplib
from email.message import EmailMessage
import requests
import plotly.express as px

# CONFIG
MODEL_ID = "cavity-73rfa/3"
API_KEY = "byOqF4HnykvCt2y074mI"
API_URL = "https://detect.roboflow.com"
CSV_FOLDER = "patient_records"
PASSWORD = "admin123"
EMAIL_SENDER = "kamarajengg.edu.in@gmail.com"
SENDER_PASSWORD = "vwvcwsfffbrvumzh"

# UI Config
st.set_page_config(page_title="🦷 Dental Cavity Detector", layout="centered")

# Styles
st.markdown("""
    <style>
    .title { font-size: 2.5em; font-weight: bold; color: #0077b6; text-align: center; }
    .subtext { font-size: 1em; color: #333333; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# Session
for key in ["authenticated", "doctor_name", "active_patient", "role"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "authenticated" else False

# Landing
st.title("🦷 Dental Cavity Checker")
if not st.session_state.role:
    st.session_state.role = st.radio("Who are you?", ["Patient", "Doctor"])

# Doctor Interface
if st.session_state.role == "Doctor":
    if not st.session_state.authenticated:
        st.subheader("🔐 Doctor Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if password == PASSWORD:
                st.session_state.authenticated = True
                st.session_state.doctor_name = username
                st.experimental_rerun()
            else:
                st.error("❌ Invalid credentials")
    else:
        st.sidebar.title("📋 Doctor Panel")
        page = st.sidebar.selectbox("Navigate", ["🗕 Live Dashboard", "📁 Patient Records"])
        st.sidebar.button("🔒 Logout", on_click=lambda: st.session_state.update({
            "authenticated": False, "doctor_name": "", "active_patient": "", "role": None
        }))

        if page == "🗕 Live Dashboard":
            st.header("📡 Real-time Monitoring")
            patient = st.session_state.active_patient or "Waiting for patient activity..."
            st.info(f"Currently active patient: {patient}")

        elif page == "📁 Patient Records":
            st.header("📑 Patient Record Archive")

            if not os.path.exists(CSV_FOLDER):
                os.makedirs(CSV_FOLDER)

            files = [f for f in os.listdir(CSV_FOLDER) if f.endswith(".csv")]
            if not files:
                st.info("No patient records found.")
            else:
                dfs = []
                for file in files:
                    try:
                        df = pd.read_csv(os.path.join(CSV_FOLDER, file))
                        df["source_file"] = file
                        dfs.append(df)
                    except:
                        continue

                if dfs:
                    df = pd.concat(dfs, ignore_index=True)

                    with st.sidebar:
                        st.subheader("Filter Options")
                        name_filter = st.text_input("Search Name")
                        date_filter = st.date_input("Filter by Date", value=None)

                    if name_filter:
                        df = df[df['Name'].str.contains(name_filter, case=False)]

                    if date_filter:
                        date_str = date_filter.strftime("%Y-%m-%d")
                        df = df[df['Datetime'].str.startswith(date_str)]

                    st.success(f"{len(df)} record(s) found")
                    st.dataframe(df, use_container_width=True)

                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Filtered Records", csv, "records.csv", "text/csv")

                    st.markdown("---")
                    st.subheader("📊 Diagnosis Overview")
                    st.metric("Total Patients", len(df))
                    st.metric("Cavity Cases", (df["Diagnosis"] == "Cavity Detected").sum())

# Patient Interface
elif st.session_state.role == "Patient":
    if st.session_state.authenticated and st.session_state.active_patient == "":
        st.session_state.authenticated = False
        st.session_state.doctor_name = ""

    st.header("📝 Patient Information")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Patient Name")
    with col2:
        contact = st.text_input("Contact Number")

    st.session_state.active_patient = name

    language = st.selectbox("🌐 Select Language for Audio", ["en", "ta", "hi"])
    email_to = st.text_input("📧 Email (optional for report)")

    st.header("📤 Upload Dental X-ray")
    uploaded_file = st.file_uploader("Choose JPG or PNG", type=["jpg", "jpeg", "png"])

    if uploaded_file and name and contact:
        st.image(uploaded_file, caption="Uploaded", use_container_width=True)
        with st.spinner("Analyzing Image..."):
            temp_path = "temp.jpg"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.read())

            image = Image.open(temp_path).convert("RGB")
            buffer = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            image.save(buffer.name)

            with open(buffer.name, "rb") as f:
                resp = requests.post(
                    f"{API_URL}/{MODEL_ID}?api_key={API_KEY}",
                    files={"file": f},
                    data={"name": "image"}
                )
                result = resp.json()

            draw = ImageDraw.Draw(image)
            cavity = False

            for pred in result.get("predictions", []):
                x, y, w, h = pred['x'], pred['y'], pred['width'], pred['height']
                if "cavity" in pred["class"].lower():
                    cavity = True
                left, top = x - w/2, y - h/2
                right, bottom = x + w/2, y + h/2
                draw.rectangle([left, top, right, bottom], outline="red", width=3)
                draw.text((left, top - 10), f"{pred['class']} ({pred['confidence']:.2f})", fill="red")

            diagnosis = "Cavity Detected" if cavity else "No Cavity Detected"
            st.success("✅ Analysis Complete")
            st.image(image, caption="Prediction", use_container_width=True)
            st.subheader(f"🧪 Diagnosis: {diagnosis}")

            text = {
                "ta": "கறைகள் கண்டறியப்பட்டுள்ளது" if cavity else "பல்லில் கறை இல்லை",
                "hi": "दाँत में कैविटी मिली है" if cavity else "कोई कैविटी नहीं पाई गई",
                "en": f"Diagnosis is: {diagnosis}"
            }[language]

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tf:
                gTTS(text, lang=language).save(tf.name)
                audio_path = tf.name
                audio_base64 = base64.b64encode(open(audio_path, 'rb').read()).decode()
                st.markdown(f"""
                    <audio autoplay>
                        <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                    </audio>
                """, unsafe_allow_html=True)

            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record = pd.DataFrame([{
                "Name": name, "Contact": contact,
                "Datetime": now, "Diagnosis": diagnosis
            }])

            os.makedirs(CSV_FOLDER, exist_ok=True)
            filename = f"{name.replace(' ', '_')}_{now[:10]}.csv"
            record.to_csv(os.path.join(CSV_FOLDER, filename), index=False)

            if email_to:
                try:
                    msg = EmailMessage()
                    msg["Subject"] = "Dental Cavity Diagnosis"
                    msg["From"] = EMAIL_SENDER
                    msg["To"] = email_to
                    msg.set_content(f"Patient: {name}\nDiagnosis: {diagnosis}\nDate: {now}")

                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
                        smtp.send_message(msg)

                    st.success("📧 Email sent successfully.")
                except Exception as e:
                    st.warning(f"Email failed: {e}")

st.markdown("---")
st.markdown("Built by Sakthi | Powered by Roboflow & Streamlit")
