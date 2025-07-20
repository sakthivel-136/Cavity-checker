from streamlit_drawable_canvas import st_canvas
import streamlit as st
from PIL import Image, ImageDraw
import requests
import tempfile
import base64
from gtts import gTTS
import math

st.set_page_config(page_title="Mark & Detect Cavity", layout="centered")
st.title("🦷 Mark Area to Detect Cavity (AI + Manual)")

image_file = st.file_uploader("Upload Dental X-ray", type=["jpg", "jpeg", "png"])

if image_file:
    img = Image.open(image_file).convert("RGB")
    w, h = img.size

    st.markdown("✍️ Mark the area to check (draw a dot or box):")
    canvas_result = st_canvas(
        fill_color="rgba(255, 0, 0, 0.3)",  # red transparent
        stroke_width=3,
        stroke_color="red",
        background_image=img,
        update_streamlit=True,
        height=h,
        width=w,
        drawing_mode="point",  # point = single click
        key="canvas",
    )

    if canvas_result.json_data is not None:
        objects = canvas_result.json_data["objects"]
        if len(objects) > 0:
            x_click = objects[0]["left"]
            y_click = objects[0]["top"]
            st.success(f"🔍 You clicked at: ({int(x_click)}, {int(y_click)})")

            # Step 3: Run Roboflow Detection
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                img.save(tmp.name)
                with open(tmp.name, "rb") as f:
                    response = requests.post(
                        "https://detect.roboflow.com/YOUR_MODEL_ID?api_key=YOUR_API_KEY",
                        files={"file": f}
                    )

            result = response.json()
            predictions = result.get("predictions", [])

            # Step 4: Draw only near clicked area
            draw = ImageDraw.Draw(img)
            found = False
            for pred in predictions:
                x, y, w_box, h_box = pred["x"], pred["y"], pred["width"], pred["height"]
                dist = math.sqrt((x - x_click) ** 2 + (y - y_click) ** 2)
                if dist < 100:
                    found = True
                    draw.rectangle([(x - w_box / 2, y - h_box / 2), (x + w_box / 2, y + h_box / 2)], outline="red", width=3)
                    draw.text((x - w_box / 2, y - h_box / 2 - 10), f"{pred['class']} ({pred['confidence']:.2f})", fill="red")

            st.image(img, caption="🔎 Filtered AI Prediction", use_column_width=True)

            # Step 5: Voice feedback
            message = "Cavity found in selected area" if found else "No cavity detected near your selection"
            st.success(f"🩺 Result: {message}")

            tts = gTTS(message, lang='en')
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(tfile.name)
            audio_data = base64.b64encode(open(tfile.name, 'rb').read()).decode()
            st.markdown(f"""
            <audio autoplay>
              <source src="data:audio/mp3;base64,{audio_data}" type="audio/mp3">
            </audio>
            """, unsafe_allow_html=True)
