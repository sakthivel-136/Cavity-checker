import streamlit as st
import os
import pandas as pd
from datetime import datetime
import base64
from PIL import Image
import smtplib
from email.message import EmailMessage

st.set_page_config(page_title="Doctor Dashboard", layout="wide")
st.title("🦷 Doctor Dashboard – Cavity Detection Reports")

record_dir = "patient_records"  # this folder should contain one CSV per patient
image_dir = "patient_images"  # folder where images are stored

if not os.path.exists(record_dir):
    st.warning(f"'{record_dir}' directory not found. Please make sure patient records are saved there.")
    st.stop()

# Gather all records
patient_files = [f for f in os.listdir(record_dir) if f.endswith(".csv")]

if not patient_files:
    st.info("No patient records found yet.")
    st.stop()

all_records = []
for file in patient_files:
    path = os.path.join(record_dir, file)
    try:
        df = pd.read_csv(path)
        df["source_file"] = file
        all_records.append(df)
    except Exception as e:
        st.error(f"Error reading {file}: {e}")

if not all_records:
    st.info("No valid records to display.")
    st.stop()

# Combine all data
records_df = pd.concat(all_records, ignore_index=True)

# Optional filters
with st.sidebar:
    st.subheader("🔍 Filter Options")
    name_filter = st.text_input("Search by Name")
    date_filter = st.date_input("Filter by Date", value=None)

# Apply filters
if name_filter:
    records_df = records_df[records_df['Name'].str.contains(name_filter, case=False)]

if date_filter:
    date_str = date_filter.strftime("%Y-%m-%d")
    records_df = records_df[records_df['Datetime'].str.startswith(date_str)]

# Display
st.success(f"{len(records_df)} patient record(s) found")
st.dataframe(records_df, use_container_width=True)

# Download
csv = records_df.to_csv(index=False).encode('utf-8')
st.download_button("Download Filtered Records", csv, "filtered_records.csv", "text/csv")

# Show statistics
st.markdown("---")
st.subheader("📈 Diagnosis Summary")
st.metric("Total Patients", len(records_df))
st.metric("Cavity Cases", (records_df['Diagnosis'] == 'Cavity Detected').sum())

# Show patient images and email option
st.markdown("---")
st.subheader("🖼 View Patient Images and Email")

for i, row in records_df.iterrows():
    name = row['Name']
    diagnosis = row['Diagnosis']
    datetime_str = row['Datetime']
    filename_base = f"{name}_{datetime_str.replace(':', '-').replace(' ', '_')}"
    image_path = os.path.join(image_dir, f"{filename_base}.jpg")

    st.markdown(f"### 🧑‍⚕️ {name} – {datetime_str}")
    st.write(f"**Diagnosis**: {diagnosis}")

    if os.path.exists(image_path):
        st.image(image_path, caption=f"Uploaded by {name}", use_column_width=True)
        email_to = st.text_input(f"Send diagnosis for {name} to email:", key=f"email_{i}")
        if st.button(f"Send Email to {name}", key=f"btn_{i}"):
            try:
                EMAIL_SENDER = "your_email@gmail.com"
                EMAIL_PASSWORD = "your_email_password"
                msg = EmailMessage()
                msg['Subject'] = 'Dental Cavity Diagnosis Report'
                msg['From'] = EMAIL_SENDER
                msg['To'] = email_to
                msg.set_content(f"Patient Name: {name}\nDiagnosis: {diagnosis}\nDate: {datetime_str}")
                with open(image_path, 'rb') as img_file:
                    img_data = img_file.read()
                    msg.add_attachment(img_data, maintype='image', subtype='jpeg', filename=os.path.basename(image_path))
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                    smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
                    smtp.send_message(msg)
                st.success("✅ Email sent successfully")
            except Exception as e:
                st.error(f"❌ Failed to send email: {e}")
    else:
        st.warning("No image found for this patient.")
