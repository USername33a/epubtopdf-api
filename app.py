from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os, uuid, io
from ebooklib import epub
from bs4 import BeautifulSoup
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image as RLImage, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from PIL import Image
import pytesseract

app = Flask(__name__)
CORS(app)

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Optional: set pytesseract executable if using local Tesseract
# Example if you deploy with a container and Tesseract is installed:
# pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

@app.route("/")
def home():
    return jsonify({"status": "EPUB to PDF API running on Render"})

@app.route("/convert", methods=["POST"])
def convert_epub_to_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename.lower().endswith(".epub"):
        return jsonify({"error": "Only EPUB files allowed"}), 400

    uid = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_FOLDER, f"{uid}.epub")
    output_path = os.path.join(OUTPUT_FOLDER, f"{uid}.pdf")
    file.save(input_path)

    try:
        book = epub.read_epub(input_path)
        styles = getSampleStyleSheet()
        story = []
        found_content = False

        # Extract text and images
        for item in book.get_items():
            if item.get_type() == epub.ITEM_DOCUMENT:
                html = item.get_content().decode("utf-8", errors="ignore")
                soup = BeautifulSoup(html, "html.parser")
                for para in soup.find_all(["p", "div", "span"]):
                    text = para.get_text().strip()
                    if text:
                        story.append(Paragraph(text, styles["Normal"]))
                        story.append(Spacer(1, 8))
                        found_content = True

            elif item.get_type() == epub.ITEM_IMAGE:
                img_bytes = item.get_content()
                img_stream = io.BytesIO(img_bytes)
                try:
                    pil_img = Image.open(img_stream)
                    # OCR on image
                    text = pytesseract.image_to_string(pil_img)
                    if text.strip():
                        story.append(Paragraph(text, styles["Normal"]))
                        story.append(Spacer(1, 8))
                    # Add image itself
                    img_stream.seek(0)
                    rl_img = RLImage(img_stream, width=400, preserveAspectRatio=True)
                    story.append(rl_img)
                    story.append(Spacer(1, 12))
                    found_content = True
                except Exception as e:
                    print("Image OCR failed:", e)

        if not found_content:
            return jsonify({"error": "No readable text or images found in EPUB"}), 500

        # Build PDF
        doc = SimpleDocTemplate(output_path)
        doc.build(story)

        return send_file(
            output_path,
            as_attachment=True,
            download_name="converted.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        return jsonify({"error": "Exception", "details": str(e)}), 500
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

# ✅ Updated to use Render's dynamic PORT environment variable
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))  # Render sets PORT automatically
    app.run(host="0.0.0.0", port=port)
