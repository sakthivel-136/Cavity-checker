# 🦷 Dental Cavity Detection with Login, Admin Dashboard, Charts, Email, and Multi-Language TTS
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
import plotly.express as px
import requests

# ========== CONFIGURATION ==========
MODEL_ID = "cavity-73rfa/3"
API_KEY = "byOqF4HnykvCt2y074mI"
API_URL = "https://detect.roboflow.com"
CSV_LOG = "patient_records.csv"
PASSWORD = "admin123"
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_email_password"

# ========== STYLING ==========
st.set_page_config(page_title="🦷 Dental Cavity Detector", layout="centered")

st.markdown("""
    <style>
    .title {
        font-size: 2.5em;
        font-weight: bold;
        color: #0077b6;
        text-align: center;
    }
    .subtext {
        font-size: 1em;
        color: #333333;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# ========== SESSION STATE INIT ==========
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "doctor_name" not in st.session_state:
    st.session_state.doctor_name = ""
if "active_patient" not in st.session_state:
    st.session_state.active_patient = ""
if "role" not in st.session_state:
    st.session_state.role = None

# ========== ROLE SELECTION ==========
st.title("🦷 Dental Cavity Checker")
if not st.session_state.role:
    st.session_state.role = st.radio("Who are you?", ["Patient", "Doctor"])

role = st.session_state.role

if role == "Doctor":
    if not st.session_state.authenticated:
        st.markdown("<h2>🔐 Doctor Login</h2>", unsafe_allow_html=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if password == PASSWORD:
                st.session_state.authenticated = True
                st.session_state.doctor_name = username
                st.rerun()
            else:
                st.error("❌ Invalid credentials")

elif role == "Patient":
    if st.session_state.authenticated and st.session_state.active_patient == "":
        st.session_state.authenticated = False
        st.session_state.doctor_name = ""

    st.header("📋 Patient Information")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Patient Name")
    with col2:
        contact = st.text_input("Contact Number")

    st.session_state.active_patient = name

    language = st.selectbox("🌤 Choose Language for TTS", ["en", "ta", "hi"])
    email_to = st.text_input("Send Report to Email (Optional)")

    st.header("📄 Upload Dental X-ray")
    uploaded_file = st.file_uploader("Choose an image (JPG/PNG)", type=["jpg", "jpeg", "png"])

    if uploaded_file and name and contact:
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        with st.spinner("Analyzing with AI..."):
            img_path = "temp_image.jpg"
            with open(img_path, "wb") as f:
                f.write(uploaded_file.read())

            image = Image.open(img_path).convert("RGB")
            buffered = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            image.save(buffered.name)

            with open(buffered.name, "rb") as f:
                response = requests.post(
                    f"{API_URL}/{MODEL_ID}?api_key={API_KEY}",
                    files={"file": f},
                    data={"name": "image"}
                )
                result = response.json()

            draw = ImageDraw.Draw(image)
            cavity_found = False

            for pred in result.get('predictions', []):
                x, y, w, h = pred['x'], pred['y'], pred['width'], pred['height']
                class_name = pred['class']
                conf = pred['confidence']

                if "cavity" in class_name.lower():
                    cavity_found = True

                left = x - w / 2
                top = y - h / 2
                right = x + w / 2
                bottom = y + h / 2

                draw.rectangle([left, top, right, bottom], outline="red", width=3)
                draw.text((left, top - 10), f"{class_name} ({conf:.2f})", fill="red")

            st.success("✅ Analysis Complete")
            st.image(image, caption="Prediction Output", use_container_width=True)

            diagnosis = "Cavity Detected" if cavity_found else "No Cavity Detected"
            st.subheader(f"🧪 Diagnosis: {diagnosis}")

            if language == "ta":
                text_to_speak = "கறைகள் கண்டறியப்பட்டுள்ளது" if cavity_found else "பல்லில் கறை இல்லை"
            elif language == "hi":
                text_to_speak = "दाँत में कैविटी मिली है" if cavity_found else "कोई कैविटी नहीं पाई गई"
            else:
                text_to_speak = f"Diagnosis is: {diagnosis}"

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tf:
                tts = gTTS(text=text_to_speak, lang=language)
                tts.save(tf.name)

            # Embed audio autoplay
            audio_path = tf.name
            audio_base64 = base64.b64encode(open(audio_path, 'rb').read()).decode()
            audio_html = f"""
                <audio autoplay>
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                </audio>
            """
            st.markdown(audio_html, unsafe_allow_html=True)

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{
                "Name": name,
                "Contact": contact,
                "Datetime": timestamp,
                "Diagnosis": diagnosis
            }])

            if os.path.exists(CSV_LOG):
                existing = pd.read_csv(CSV_LOG)
                updated = pd.concat([existing, new_row], ignore_index=True)
            else:
                updated = new_row

            updated.to_csv(CSV_LOG, index=False)
            st.success("✅ Patient record saved.")

            if email_to:
                try:
                    msg = EmailMessage()
                    msg["Subject"] = "Dental Cavity Diagnosis"
                    msg["From"] = EMAIL_SENDER
                    msg["To"] = email_to
                    msg.set_content(f"Patient Name: {name}\nDiagnosis: {diagnosis}\nDate: {timestamp}")

                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
                        smtp.send_message(msg)

                    st.success("📧 Email sent successfully")
                except Exception as e:
                    st.warning(f"Email failed: {e}")

if st.session_state.authenticated:
    page = st.sidebar.selectbox("Navigate", ["📅 Live Dashboard", "📁 Patient Records"])
    if page == "📅 Live Dashboard":
        st.header(f"🔎 Live View: {st.session_state.active_patient if st.session_state.active_patient else 'Waiting for patient...'}")
        st.info("This page can be used to observe real-time uploads from the patient's end.")

    elif page == "📁 Patient Records":
        st.header("📈 Patient Records Overview")
        if os.path.exists(CSV_LOG):
            df = pd.read_csv(CSV_LOG)
            st.dataframe(df, use_container_width=True)

            st.markdown("---")
            st.subheader("📈 Diagnosis Summary")
            st.metric("Total Patients", len(df))
            st.metric("Cavity Cases", (df['Diagnosis'] == 'Cavity Detected').sum())
            chart = px.histogram(df, x="Datetime", color="Diagnosis", title="🕒 Daily Case Log")
            st.plotly_chart(chart, use_container_width=True)

            csv = df.to_csv(index=False).encode()
            st.download_button("⬇️ Download CSV", csv, "patient_records.csv", "text/csv")
        else:
            st.info("No records found yet.")

    st.sidebar.button("🔒 Logout", on_click=lambda: st.session_state.update({"authenticated": False, "doctor_name": "", "active_patient": "", "role": None}))

st.markdown("---")
st.markdown("Built with ❤️ by Sakthi | Powered by Roboflow, Streamlit, and GPT")
