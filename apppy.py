import streamlit as st
from PIL import Image, ImageDraw
import requests
import tempfile
import base64
from gtts import gTTS
import math

st.set_page_config(page_title="Mark-and-Detect", layout="centered")
st.title("🦷 Mark Area & Detect Cavity (User + AI)")

# Upload image
image_file = st.file_uploader("Upload Dental X-ray", type=["jpg", "jpeg", "png"])
if image_file:
    img = Image.open(image_file).convert("RGB")
    w, h = img.size
    st.image(img, caption="Click on the area you want AI to check", use_column_width=True)

    # Let user click on the image
    coords = st.image_coordinates(image_file)
    if coords:
        x_click, y_click = coords['x'], coords['y']
        st.success(f"🔍 You clicked at: ({int(x_click)}, {int(y_click)})")

        # Run Roboflow API detection
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            img.save(tmp.name)
            with open(tmp.name, "rb") as f:
                response = requests.post(
                    "https://detect.roboflow.com/YOUR_MODEL_ID?api_key=YOUR_API_KEY",
                    files={"file": f}
                )

        predictions = response.json().get("predictions", [])
        st.info(f"Total predictions by AI: {len(predictions)}")

        # Filter: Only show predictions near the clicked point
        draw = ImageDraw.Draw(img)
        nearby_found = False
        for pred in predictions:
            x, y, w_box, h_box = pred["x"], pred["y"], pred["width"], pred["height"]
            dist = math.sqrt((x - x_click)**2 + (y - y_click)**2)
            if dist < 100:  # only show if within 100px radius
                draw.rectangle([(x - w_box/2, y - h_box/2), (x + w_box/2, y + h_box/2)], outline="red", width=3)
                draw.text((x - w_box/2, y - h_box/2 - 10), f"{pred['class']} ({pred['confidence']:.2f})", fill="red")
                nearby_found = True

        st.image(img, caption="Filtered AI Predictions Near Your Mark", use_column_width=True)

        # Speak result
        if nearby_found:
            msg = "Cavity found near the selected area"
        else:
            msg = "No cavity detected in the selected region"

        st.success(f"🩺 Result: {msg}")

        tts = gTTS(msg, lang='en')
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tfile.name)
        audio_data = base64.b64encode(open(tfile.name, 'rb').read()).decode()
        st.markdown(f"""
        <audio autoplay>
          <source src="data:audio/mp3;base64,{audio_data}" type="audio/mp3">
        </audio>
        """, unsafe_allow_html=True)
