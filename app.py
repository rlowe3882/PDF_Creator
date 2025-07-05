import streamlit as st
import fitz
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame
from openai import OpenAI
from dotenv import load_dotenv
import os
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.acroform import AcroForm
import base64

# --- Load environment ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Streamlit UI ---
st.set_page_config(page_title="PDF Customizer", layout="centered")
st.title("🎨 AI-Powered PDF Customizer with Fillable Fields")

uploaded_pdf = st.file_uploader("Upload a PDF", type="pdf")
tone = st.selectbox("Choose a tone", ["Professional", "Friendly", "Legalese", "Conversational"])
primary_color = st.color_picker("Pick a primary brand color", "#003366")
company_name = st.text_input("Enter your company name (optional)")
logo_file = st.file_uploader("Upload your company logo (PNG/JPG)", type=["png", "jpg", "jpeg"])

if not OPENAI_API_KEY:
    st.error("⚠️ OpenAI API key not found. Please set it in your .env file.")
    st.stop()

# --- Helpers ---
def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def rewrite_text_with_openai(text, tone):
    client = OpenAI(api_key=OPENAI_API_KEY)
    messages = [
        {"role": "system", "content": f"You are a helpful assistant rewriting documents in a {tone.lower()} tone."},
        {"role": "user", "content": f"Rewrite the following content:\n{text}"}
    ]
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages
    )
    return response.choices[0].message.content.strip()

def create_pdf_with_fields(text, output_path, color_hex, company_name=None, logo_path=None):
    c = canvas.Canvas(output_path, pagesize=LETTER)
    form = c.acroForm
    width, height = LETTER
    y = height - 72

    # Logo
    if logo_path:
        try:
            logo = ImageReader(logo_path)
            c.drawImage(logo, 72, y - 50, width=100, preserveAspectRatio=True, mask='auto')
            y -= 60
        except:
            pass

    # Company name
    if company_name:
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(colors.HexColor(color_hex))
        c.drawString(72, y, company_name)
        y -= 30

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)

    lines = text.split('\n')
    for line in lines:
        c.drawString(72, y, line)

        # Add textbox if the line suggests a field
        if any(k in line.lower() for k in ["your name", "signature", "date", "email", "phone"]):
            field_name = line.lower().replace(" ", "_")[:20]
            form.textfield(name=field_name, tooltip=line, x=250, y=y - 4, width=200, height=14,
                           borderStyle='underlined', fillColor=None, textColor=colors.black)

        y -= 20
        if y < 100:
            c.showPage()
            y = height - 72
            c.setFont("Helvetica", 10)

    c.save()

# --- Main Logic ---
if uploaded_pdf and st.button("✨ Customize and Generate PDF"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_input:
        tmp_input.write(uploaded_pdf.read())
        tmp_input_path = tmp_input.name

    with st.spinner("🔍 Extracting text..."):
        pdf_text = extract_pdf_text(tmp_input_path)

    with st.spinner("🤖 Rewriting with OpenAI..."):
        rewritten = rewrite_text_with_openai(pdf_text, tone)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_output:
        logo_path = None
        if logo_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
                tmp_logo.write(logo_file.read())
                logo_path = tmp_logo.name

        create_pdf_with_fields(rewritten, tmp_output.name, primary_color, company_name, logo_path)

        # Read final PDF
        with open(tmp_output.name, "rb") as f:
            pdf_data = f.read()

        # Download
        st.success("✅ PDF customized successfully!")
        st.download_button("📥 Download Fillable PDF", data=pdf_data, file_name="customized_fillable.pdf")

        # Live preview
        base64_pdf = base64.b64encode(pdf_data).decode("utf-8")
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown("#### 📄 Live Preview Below")
        st.components.v1.html(pdf_display, height=600)
