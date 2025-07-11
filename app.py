
import streamlit as st
import tempfile
import fitz  # PyMuPDF
from openai import OpenAI
from dotenv import load_dotenv
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- Load environment ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Register Unicode-Compatible Fonts ---
pdfmetrics.registerFont(TTFont("NotoSans", "fonts/NotoSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("NotoSansJP", "fonts/NotoSansJP-Regular.ttf"))
pdfmetrics.registerFont(TTFont("NotoSansSC", "fonts/NotoSansSC-Regular.ttf"))
pdfmetrics.registerFont(TTFont("NotoSansArabic", "fonts/NotoSansArabic-Regular.ttf"))

# --- Language to Font mapping ---
LANG_FONT_MAP = {
    "Japanese": "NotoSansJP",
    "Chinese": "NotoSansSC",
    "Arabic": "NotoSansArabic"
}

# --- Streamlit UI ---
st.set_page_config(page_title="AI PDF Rewriter, Translator & Summarizer", layout="centered")
st.title("📝 AI-Powered PDF Rewriter, Translator & Summarizer")

uploaded_pdf = st.file_uploader("Upload a PDF file", type="pdf")

mode = st.selectbox("Choose an action:", [
    "Rewrite Tone (Professional / Conversational / Legalese)",
    "Translate to Another Language"
])

summarize = st.checkbox("🔍 Summarize this document instead")

if mode.startswith("Rewrite"):
    tone = st.selectbox("Select desired tone:", ["Professional", "Friendly", "Conversational", "Legalese"])
    target_lang = None
else:
    target_lang = st.selectbox("Translate to language:", ["Spanish", "French", "Japanese", "Hindi", "German", "Chinese", "Arabic", "Italian"])

primary_color = st.color_picker("Highlight color", "#003366")

if not OPENAI_API_KEY:
    st.error("❗ OpenAI API key missing. Please set it in your .env file.")
    st.stop()

# --- Helpers ---
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text() for page in doc])
    doc.close()
    return text

def wrap_text(text, canvas_obj, max_width, font, font_size):
    canvas_obj.setFont(font, font_size)
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if canvas_obj.stringWidth(test_line, font, font_size) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

def create_pdf_from_text(text, output_path, color_hex, font="NotoSans", font_size=10):
    from reportlab.lib.units import inch

    c = canvas.Canvas(output_path, pagesize=LETTER)
    width, height = LETTER
    margin = 1 * inch
    max_width = width - 2 * margin
    y = height - 72

    c.setFont(font, font_size + 6)
    c.setFillColor(colors.HexColor(color_hex))
    c.drawString(margin, y, "AI-Generated Document")
    y -= 36

    c.setFont(font, font_size)
    c.setFillColor(colors.black)

    for paragraph in text.split("\n"):
        wrapped_lines = wrap_text(paragraph.strip(), c, max_width, font, font_size)
        for line in wrapped_lines:
            c.drawString(margin, y, line)
            y -= font_size + 4
            if y < 72:
                c.showPage()
                y = height - 72
                c.setFont(font, font_size)

    c.save()

# --- Main logic ---
if uploaded_pdf and st.button("🔁 Process Document"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_pdf.read())
        input_path = tmp_file.name

    with st.spinner("📖 Extracting text..."):
        extracted_text = extract_text_from_pdf(input_path)
    if not extracted_text.strip():
        st.error("❗ No text found in the PDF. Please upload a valid PDF with text content.")
        st.stop()

    with st.spinner("🤖 Processing with OpenAI..."):
        if summarize:
            prompt = f"Summarize the following document clearly and briefly:\n\n{extracted_text}"
        elif mode.startswith("Rewrite"):
            prompt = f"Rewrite the following text in a {tone.lower()} tone:\n\n{extracted_text}"
        else:
            prompt = f"Translate the following text into {target_lang}:\n\n{extracted_text}"

        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful document assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        processed_text = response.choices[0].message.content.strip()

    selected_font = LANG_FONT_MAP.get(target_lang, "NotoSans")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as out_pdf:
        create_pdf_from_text(
            processed_text,
            out_pdf.name,
            color_hex=primary_color,
            font=selected_font,
            font_size=10
        )
        with open(out_pdf.name, "rb") as f:
            final_data = f.read()

        st.success("✅ Document processed successfully!")
        st.download_button("📥 Download Modified PDF", data=final_data, file_name="modified_output.pdf")

        