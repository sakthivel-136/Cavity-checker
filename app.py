# All-in-One Dental Cavity Detection App
# -----------------------------------------------------
import streamlit as st
import os
from datetime import datetime
from PIL import Image, ImageDraw, UnidentifiedImageError
import pandas as pd
import base64
import tempfile
import smtplib
from email.message import EmailMessage
import requests
from gtts import gTTS
import io
import zipfile

# ================= Page Setup =================
st.set_page_config(page_title="Dental Cavity App", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "login"
if "doctor_authenticated" not in st.session_state:
    st.session_state.doctor_authenticated = False

# ================= Page 1: Login =================
def page_login():
    st.title("🦷 Welcome to the Dental Cavity Detection System")
    st.markdown("""
    <style>
    .big-font { font-size:200%; font-weight: bold; text-align: center; }
    </style>""", unsafe_allow_html=True)
    st.markdown("<p class='big-font'>Who are you?</p>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("👨‍⚕️ Doctor"):
            st.session_state.page = "doctor_login"
            st.rerun()
    with col2:
        if st.button("🧑‍ Patient"):
            st.session_state.page = "patient"
            st.rerun()

# ================= Doctor Login =================
def page_doctor_login():
    st.subheader("🔒 Doctor Login")
    password = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        if password == "admin123":  # Replace with a secure check in production
            st.session_state.doctor_authenticated = True
            st.session_state.page = "doctor"
            st.rerun()
        else:
            st.error("❌ Incorrect password")
    if st.button("⬅️ Back"):
        st.session_state.page = "login"
        st.rerun()

# ================= Page 2: Patient Upload =================
def page_patient_upload():
    st.title("📝 Patient Information & Upload")
    name = st.text_input("👤 Name")
    contact = st.text_input("📱 Contact Number")
    lang = st.selectbox("🌐 Choose Language", ["en", "ta", "hi"])
    st.session_state.language = lang

    image = st.file_uploader("📤 Upload Dental X-ray", type=["jpg", "jpeg", "png"])
    if st.button("➡️ Submit and Diagnose") and name and contact and image:
        try:
            dt_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            filename_base = f"{name}_{dt_str.replace(':', '-').replace(' ', '_')}"

            os.makedirs("patient_images", exist_ok=True)
            image_path = os.path.join("patient_images", f"{filename_base}.jpg")
            with Image.open(image) as img:
                rgb_img = img.convert("RGB")
                rgb_img.save(image_path)

            os.makedirs("patient_records", exist_ok=True)
            with open(os.path.join("patient_records", f"{filename_base}.csv"), "w") as f:
                f.write("Name,Contact,Datetime,ImagePath,Diagnosis\n")
                f.write(f"{name},{contact},{dt_str},{image_path},Pending\n")

            st.session_state.patient_name = name
            st.session_state.image_path = image_path
            st.session_state.timestamp = dt_str
            st.session_state.page = "result"
            st.rerun()
        except UnidentifiedImageError:
            st.error("❌ The uploaded file is not a valid image. Please upload a valid JPG or PNG file.")
        except Exception as e:
            st.error(f"❌ Error processing image: {e}")

# ================= Page 3: Result =================
def page_result():
    st.title("🧪 Diagnosis Result")
    image_path = st.session_state.image_path
    name = st.session_state.patient_name
    timestamp = st.session_state.timestamp
    language = st.session_state.language

    MODEL_ID = "cavity-73rfa/3"
    API_KEY = "byOqF4HnykvCt2y074mI"
    API_URL = "https://detect.roboflow.com"
    EMAIL_SENDER = "kamarajengg.edu.in@gmail.com"
    EMAIL_PASSWORD = "vwvcwsfffbrvumzh"

    img = Image.open(image_path).convert("RGB")
    with open(image_path, "rb") as f:
        response = requests.post(f"{API_URL}/{MODEL_ID}?api_key={API_KEY}", files={"file": f})

    result = response.json()
    draw = ImageDraw.Draw(img)
    cavity_found = False
    for pred in result.get("predictions", []):
        if "cavity" in pred['class'].lower():
            cavity_found = True
        x, y, w, h = pred['x'], pred['y'], pred['width'], pred['height']
        draw.rectangle([(x - w/2, y - h/2), (x + w/2, y + h/2)], outline="red", width=3)
        draw.text((x - w/2, y - h/2 - 10), f"{pred['class']} ({pred['confidence']:.2f})", fill="red")

    st.image(img, caption="AI Prediction Result", use_container_width=True)
    diagnosis = "Cavity Detected" if cavity_found else "No Cavity Detected"
    st.success(f"🩺 Diagnosis: {diagnosis}")

    record_file = os.path.join("patient_records", f"{name}_{timestamp.replace(':', '-').replace(' ', '_')}.csv")
    if os.path.exists(record_file):
        df = pd.read_csv(record_file)
        df.loc[0, 'Diagnosis'] = diagnosis
        df.to_csv(record_file, index=False)

    speak_text = {
        "ta": "கறைகள் கண்டறியப்பட்டுள்ளது" if cavity_found else "பல்லில் கறை இல்லை",
        "hi": "दाँत में कैविटी मिली है" if cavity_found else "कोई कैविटी नहीं पाई गई",
    }.get(language, diagnosis)

    tts = gTTS(speak_text, lang=language)
    audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(audio_file.name)
    audio_data = base64.b64encode(open(audio_file.name, 'rb').read()).decode()
    st.markdown(f"""
    <audio autoplay>
      <source src="data:audio/mp3;base64,{audio_data}" type="audio/mp3">
    </audio>
    """, unsafe_allow_html=True)

    email_to = st.text_input("📧 Send diagnosis via email (optional):")
    if st.button("Send Email") and email_to:
        try:
            msg = EmailMessage()
            msg['Subject'] = "Dental Cavity Diagnosis"
            msg['From'] = EMAIL_SENDER
            msg['To'] = email_to
            msg.set_content(f"Patient: {name}\nDiagnosis: {diagnosis}\nTime: {timestamp}")
            with open(image_path, 'rb') as f:
                msg.add_attachment(f.read(), maintype='image', subtype='jpeg', filename=os.path.basename(image_path))
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
                smtp.send_message(msg)
            st.success("✅ Email sent!")
        except Exception as e:
            st.error(f"Email failed: {e}")

# ================= Page 4: Doctor Dashboard =================
def page_doctor():
    st.title("🦷 Doctor Dashboard – Cavity Detection Reports")
    if st.button("🔒 Logout"):
        st.session_state.page = "login"
        st.session_state.rerun = True

    record_dir = "patient_records"
    image_dir = "patient_images"
    if not os.path.exists(record_dir):
        st.warning("No patient record directory found.")
        return

    patient_files = [f for f in os.listdir(record_dir) if f.endswith(".csv")]
    if not patient_files:
        st.info("No patient records yet.")
        return

    all_records = []
    for file in patient_files:
        try:
            df = pd.read_csv(os.path.join(record_dir, file))
            df["source_file"] = file
            all_records.append(df)
        except Exception as e:
            st.error(f"Error reading {file}: {e}")

    records_df = pd.concat(all_records, ignore_index=True)

    with st.sidebar:
        st.subheader("🔍 Filter Options")
        name_filter = st.text_input("Search by Name")
        date_filter = st.date_input("Filter by Date", value=None)

    if name_filter:
        records_df = records_df[records_df['Name'].str.contains(name_filter, case=False)]
    if date_filter:
        date_str = date_filter.strftime("%Y-%m-%d")
        records_df = records_df[records_df['Datetime'].str.startswith(date_str)]

    st.success(f"{len(records_df)} patient record(s) found")
    st.dataframe(records_df, use_container_width=True)

    csv = records_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Filtered Records", csv, "filtered_records.csv", "text/csv")

    if os.path.exists(image_dir):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for f in os.listdir(image_dir):
                zip_file.write(os.path.join(image_dir, f), arcname=f)
        st.download_button("📦 Download All Patient Images", zip_buffer.getvalue(), "all_patient_images.zip", "application/zip")

    st.subheader("📈 Diagnosis Summary")
    st.metric("Total Patients", len(records_df))
    st.metric("Cavity Cases", (records_df['Diagnosis'] == 'Cavity Detected').sum())

    for i, row in records_df.iterrows():
        name = row['Name']
        diagnosis = row['Diagnosis']
        datetime_str = row['Datetime']
        filename_base = f"{name}_{datetime_str.replace(':', '-').replace(' ', '_')}"
        image_path = os.path.join(image_dir, f"{filename_base}.jpg")

        st.markdown(f"### 🧑‍⚕️ {name} – {datetime_str}")
        st.write(f"**Diagnosis**: {diagnosis}")

        if os.path.exists(image_path):
            st.image(image_path, caption=f"Uploaded by {name}", use_container_width=True)
            email_to = st.text_input(f"Send diagnosis for {name} to email:", key=f"email_{i}")
            if st.button(f"Send Email to {name}", key=f"btn_{i}"):
                try:
                    msg = EmailMessage()
                    msg['Subject'] = 'Dental Cavity Diagnosis Report'
                    msg['From'] = EMAIL_SENDER
                    msg['To'] = email_to
                    msg.set_content(f"Patient Name: {name}\nDiagnosis: {diagnosis}\nDate: {datetime_str}")
                    with open(image_path, 'rb') as img_file:
                        msg.add_attachment(img_file.read(), maintype='image', subtype='jpeg', filename=os.path.basename(image_path))
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
                        smtp.send_message(msg)
                    st.success("✅ Email sent successfully")
                except Exception as e:
                    st.error(f"❌ Failed to send email: {e}")
        else:
            st.warning("No image found for this patient.")

# ================= Main Dispatcher =================
if st.session_state.page == "login":
    page_login()
elif st.session_state.page == "doctor_login":
    page_doctor_login()
elif st.session_state.page == "patient":
    page_patient_upload()
elif st.session_state.page == "result":
    page_result()
elif st.session_state.page == "doctor":
    if st.session_state.doctor_authenticated:
        page_doctor()
    else:
        st.session_state.page = "doctor_login"
        st.rerun()


