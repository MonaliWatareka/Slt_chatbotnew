"""
image_reader.py — Vision Q&A with OCR fallback.
Uses ollama Python library (reliable) + Tesseract OCR backup.
"""

import base64
import io
import re
from PIL import Image, ImageEnhance, ImageFilter

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"E:\OCR\tesseract.exe"
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import ollama as ollama_lib
    OLLAMA_LIB_AVAILABLE = True
except ImportError:
    OLLAMA_LIB_AVAILABLE = False

def preprocess_image(image_file, max_side: int = 1024):
    try:
        image_file.seek(0)
    except Exception:
        pass

    img = Image.open(image_file)
    if img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > max_side:
        ratio = max_side / max(w, h)
        img   = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    w, h = img.size
    if max(w, h) < 400:
        img = img.resize((int(w * 2), int(h * 2)), Image.LANCZOS)

    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = ImageEnhance.Sharpness(img).enhance(2.0)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return img, buf.getvalue()

def _build_prompt(question: str) -> str:
    q = question.lower()
    base = (
        "You are reading an SLT Mobitel document. "
        "Reply ONLY in English using ASCII characters. "
        "Ignore all Sinhala and Tamil text. "
        "Use Rs. for money. Be concise.\n\n"
    )
    if any(w in q for w in ["total", "pay", "amount", "payable"]):
        return base + "What is the TOTAL PAYABLE amount? Reply: Rs. [number]"
    elif any(w in q for w in ["due", "date", "deadline"]):
        return base + "What is the Payment Due Date? Reply with date only."
    elif any(w in q for w in ["account", "number"]):
        return base + "What is the Account Number? Reply with number only."
    elif any(w in q for w in ["charge", "service", "breakdown", "list"]):
        return base + "List all charges with Rs. amounts. One per line."
    elif any(w in q for w in ["summary", "all", "everything"]):
        return base + "Summarize all key details: account, period, charges, total, due date."
    else:
        return base + f"Question: {question}\nAnswer:"

def _clean_text(text: str) -> str:
    text = re.sub(r'[\u0B80-\u0BFF\u0D80-\u0DFF\u0E00-\u0E7F]+', '', text)
    text = re.sub(r'[^\x00-\x7F\u20A8\u20B9]+', '', text)
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines, seen = [], set()
    for line in text.split("\n"):
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    return "\n".join(lines).strip()

def extract_text_ocr(pil_image) -> str:
    if not TESSERACT_AVAILABLE:
        return ""
    try:
        # --tessdata-dir points Tesseract to the correct language data folder
        return pytesseract.image_to_string(
            pil_image,
            config=r"--psm 6 -l eng --tessdata-dir E:\OCR\tessdata"
        ).strip()
    except Exception as e:
        print(f"[image_reader] OCR error: {e}")
        return ""

def answer_from_ocr(ocr_text: str, question: str, model: str = "llama3.2") -> str:
    if not ocr_text:
        return "⚠️ OCR could not extract text from this image."
    if OLLAMA_LIB_AVAILABLE:
        try:
            resp = ollama_lib.chat(
                model=model,
                messages=[{"role": "user", "content": (
                    f"You are reading extracted text from an SLT Mobitel invoice.\n"
                    f"Answer using ONLY the text below. Reply in English.\n\n"
                    f"Text:\n{ocr_text[:3000]}\n\nQuestion: {question}\nAnswer:"
                )}],
                options={"temperature": 0.0, "num_predict": 200},
            )
            return resp["message"]["content"].strip()
        except Exception as e:
            return f"OCR extracted text but LLM failed: {e}\n\nRaw:\n{ocr_text[:500]}"
    return f"📄 Extracted text:\n\n{ocr_text[:1500]}"

def ask_image_question(image_file, question: str, model: str = "llava") -> str:
    print(f"[image_reader] model={model} question={question[:60]}")

    try:
        pil_img, img_bytes = preprocess_image(image_file, max_side=1024)
    except Exception as e:
        return f"❌ Could not read image: {e}"

    prompt = _build_prompt(question)

    if OLLAMA_LIB_AVAILABLE:
        try:
            response = ollama_lib.chat(
                model=model,
                messages=[{
                    "role":    "user",
                    "content": prompt,
                    "images":  [img_bytes],
                }],
                options={"temperature": 0.0, "num_predict": 200},
            )
            result = _clean_text(response["message"]["content"].strip())
            if len(result) > 5:
                return result
        except ollama_lib.ResponseError as e:
            if "model not found" in str(e).lower():
                return (
                    f"❌ Model '{model}' not found.\n"
                    f"Install: `ollama pull {model}`"
                )
        except Exception as e:
            print(f"[image_reader] Vision error: {e}")

    # OCR fallback
    print("[image_reader] Falling back to OCR...")
    ocr_text = extract_text_ocr(pil_img)
    if ocr_text:
        answer = answer_from_ocr(ocr_text, question)
        return f"📄 *(via OCR fallback)*\n\n{answer}"

    return (
        "⚠️ Could not read this image.\n\n"
        "**Try:**\n"
        "- Use a clearer, well-lit photo\n"
        "- Switch to **llava** in the sidebar\n"
        "- Run `ollama serve` in a terminal\n"
        "- Install Tesseract for OCR fallback"
    )