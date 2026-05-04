"""
image_reader.py — Vision Q&A with OCR fallback
Fixed: uses ollama Python library instead of raw HTTP (no more timeouts)
New:  Tesseract OCR fallback when vision model fails
"""

import base64
import io
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

# ── Tesseract OCR (optional but recommended) ──────────────────────────────────
try:
    import pytesseract
    # If tesseract is not on PATH, set it here:
    # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# ── Ollama Python library (much more reliable than raw HTTP) ──────────────────
try:
    import ollama as ollama_lib
    OLLAMA_LIB_AVAILABLE = True
except ImportError:
    OLLAMA_LIB_AVAILABLE = False
    import httpx  # fallback to HTTP


# ─────────────────────────────────────────────────────────────────────────────
# Image preprocessing
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_image(image_file, max_side: int = 1024) -> tuple[Image.Image, bytes]:
    """Load, resize, enhance image. Returns (PIL Image, JPEG bytes)."""
    try:
        image_file.seek(0)
    except Exception:
        pass

    img = Image.open(image_file)

    # Normalize to RGB
    if img.mode not in ("RGB",):
        img = img.convert("RGB")

    w, h = img.size

    # Resize to fit within max_side
    if max(w, h) > max_side:
        ratio = max_side / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    # Upscale very small images
    w, h = img.size
    if max(w, h) < 400:
        img = img.resize((int(w * 2), int(h * 2)), Image.LANCZOS)

    # Enhance for document readability
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = ImageEnhance.Sharpness(img).enhance(2.0)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return img, buf.getvalue()


def encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# OCR fallback
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_ocr(pil_image: Image.Image) -> str:
    """Extract all text from image using Tesseract OCR."""
    if not TESSERACT_AVAILABLE:
        return ""
    try:
        # Use English + Sinhala + Tamil configs for SLT bills
        text = pytesseract.image_to_string(
            pil_image,
            config="--psm 6 -l eng",  # add +sin+tam if those packs installed
        )
        return text.strip()
    except Exception as e:
        print(f"[image_reader] OCR error: {e}")
        return ""


def answer_from_ocr_text(ocr_text: str, question: str, model: str = "llama3.2") -> str:
    """Use LLM to answer question from OCR-extracted text."""
    if not ocr_text:
        return "⚠️ OCR could not extract text from this image."

    if OLLAMA_LIB_AVAILABLE:
        prompt = f"""You are reading extracted text from an SLT Mobitel invoice/document.
Answer the question using ONLY the text below.
Reply in English. Use Rs. for money amounts.

Extracted text:
\"\"\"
{ocr_text[:3000]}
\"\"\"

Question: {question}

Answer:"""
        try:
            response = ollama_lib.chat(
            model=model,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": [img_bytes],
            }],
            options={
                "temperature": 0.0,
                "num_predict": 150,   # ADD THIS LINE — prevents infinite garbled output
            },
        )
            return response["message"]["content"].strip()
        except Exception as e:
            return f"OCR text extracted but LLM failed: {e}\n\nRaw OCR:\n{ocr_text[:500]}"
    else:
        # Return raw OCR if LLM unavailable
        return f"📄 Extracted text from image:\n\n{ocr_text[:1500]}"


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(question: str, model: str) -> str:
    question_lower = question.lower()

    is_total    = any(w in question_lower for w in ["total", "pay", "amount", "payable", "bill"])
    is_due      = any(w in question_lower for w in ["due", "date", "deadline", "when"])
    is_account  = any(w in question_lower for w in ["account", "number", "id"])
    is_charges  = any(w in question_lower for w in ["charge", "service", "breakdown", "detail", "list"])
    is_summary  = any(w in question_lower for w in ["summarize", "summary", "all", "everything"])

    base = (
    "You are reading an SLT Mobitel document. "
    "IMPORTANT: Reply ONLY in English. Use only ASCII characters 0-9 and A-Z. "
    "Do NOT output any Thai, Sinhala, Tamil, or non-Latin characters. "
    "If you see non-English text in the image, ignore it completely. "
    "Use Rs. for money amounts. Be concise.\n\n"
    )

    if is_summary:
        return base + (
            "List all key information from this document: "
            "account number, invoice number, billing period, charges, total payable, due date. "
            "Format as a neat list."
        )
    elif is_total:
        return base + "What is the TOTAL PAYABLE amount? Answer: Rs. [amount only]"
    elif is_due:
        return base + "What is the Payment Due Date? Answer with date only."
    elif is_account:
        return base + "What is the Account Number? Answer with the number only."
    elif is_charges:
        return base + "List all charges/services and their Rs. amounts. One per line."
    else:
        return base + f"Question: {question}\nAnswer:"


# ─────────────────────────────────────────────────────────────────────────────
# Main vision function — uses ollama Python library (FIXED)
# ─────────────────────────────────────────────────────────────────────────────

def ask_image_question(image_file, question: str, model: str = "moondream") -> str:
    """
    Send image + question to Ollama vision model.
    Falls back to OCR + LLM if vision model is unavailable or times out.
    """
    print(f"[image_reader] Vision request — model: {model} — question: {question[:60]}")

    # ── Preprocess image ──────────────────────────────────────
    try:
        pil_img, img_bytes = preprocess_image(image_file, max_side=896)
        img_b64 = encode_image_to_base64(img_bytes)
        print(f"[image_reader] Image ready: {len(img_bytes) // 1024} KB")
    except Exception as e:
        return f"❌ Could not read image file: {e}"

    prompt = _build_prompt(question, model)

    # ── Try ollama Python library first (MOST RELIABLE) ───────
    if OLLAMA_LIB_AVAILABLE:
        try:
            print(f"[image_reader] Using ollama library...")
            response = ollama_lib.chat(
                model=model,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": [img_bytes],   # ollama lib accepts raw bytes
                }],
                options={
                    "temperature": 0.0,
                    "num_predict": 300,
                },
            )
            result = response["message"]["content"].strip()
            result = _clean_text(result)
            if len(result) > 5:
                return result
            # Empty result — fall through to OCR
            print("[image_reader] Vision returned empty result, trying OCR...")
        except ollama_lib.ResponseError as e:
            if "model not found" in str(e).lower():
                return (
                    f"❌ Model '{model}' not found.\n\n"
                    f"Install it with:\n```\nollama pull {model}\n```\n\n"
                    "Then try again, or switch to a different vision model."
                )
            print(f"[image_reader] ollama library error: {e}, falling back to OCR...")
        except Exception as e:
            print(f"[image_reader] Vision failed: {e}, falling back to OCR...")

    # ── Fallback: raw HTTP to Ollama API ──────────────────────
    else:
        result = _ask_via_http(img_b64, prompt, model)
        if result and len(result) > 5:
            return _clean_text(result)

    # ── Last resort: OCR + LLM ────────────────────────────────
    print("[image_reader] Falling back to OCR...")
    ocr_text = extract_text_ocr(pil_img)

    if ocr_text:
        print(f"[image_reader] OCR extracted {len(ocr_text)} chars")
        answer = answer_from_ocr_text(ocr_text, question)
        return f"📄 *(Answered via OCR text extraction)*\n\n{answer}"
    else:
        return (
            "⚠️ Could not read this image with vision model or OCR.\n\n"
            "**Suggestions:**\n"
            "- Make sure the image is clear and not blurry\n"
            "- Try a brighter/higher contrast photo\n"
            "- Switch vision model in the sidebar (try **llava**)\n"
            "- Run `ollama serve` in a terminal if Ollama is not running\n\n"
            "**Install Tesseract for offline OCR fallback:**\n"
            "Download from: https://github.com/UB-Mannheim/tesseract/wiki"
        )


def _ask_via_http(img_b64: str, prompt: str, model: str) -> str:
    """Raw HTTP fallback when ollama Python library is not installed."""
    try:
        import httpx
        payload = {
            "model":  model,
            "prompt": prompt,
            "images": [img_b64],
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 300},
        }
        resp = httpx.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0),
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except httpx.ConnectError:
        return "❌ Cannot connect to Ollama. Run: `ollama serve`"
    except httpx.TimeoutException:
        return ""  # signal timeout so OCR fallback triggers
    except Exception as e:
        return f"❌ Error: {e}"


def _clean_text(text: str) -> str:
    """Remove Tamil/Sinhala chars, collapse whitespace."""
    text = re.sub(r'[\u0B80-\u0BFF\u0D80-\u0DFF]+', '', text)
    text = re.sub(r'[^\x00-\x7F\u20A8\u20B9]+', '', text)
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Deduplicate lines
    lines, seen = [], set()
    for line in text.split("\n"):
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    return "\n".join(lines).strip()