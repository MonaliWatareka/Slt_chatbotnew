import base64
import httpx
import re
from PIL import Image, ImageEnhance, ImageFilter
import io


def encode_image_to_base64(image_file, max_side: int = 900) -> str:
    """
    Preprocess and encode image.
    max_side=900 is optimal for moondream on low-RAM machines.
    """
    img = Image.open(image_file)

    # Convert to RGB
    if img.mode in ("RGBA", "P", "L", "LA"):
        img = img.convert("RGB")

    w, h = img.size
    print(f"[image_reader] Original size: {w}x{h}")

    # Resize to fit within max_side while keeping aspect ratio
    if w > max_side or h > max_side:
        ratio = min(max_side / w, max_side / h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        print(f"[image_reader] Resized to {img.size}")

    # Upscale only if very small
    w, h = img.size
    if w < 600 and h < 600:
        img = img.resize((int(w * 1.5), int(h * 1.5)), Image.LANCZOS)
        print(f"[image_reader] Upscaled to {img.size}")

    # Enhance contrast for document text
    img = ImageEnhance.Contrast(img).enhance(1.4)

    # Sharpen to help with small text
    img = img.filter(ImageFilter.SHARPEN)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)

    size_kb = len(buffer.getvalue()) / 1024
    print(f"[image_reader] Encoded size: {size_kb:.1f} KB")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _clean_response(text: str) -> str:
    """
    Remove Tamil, Sinhala, and other non-Latin characters from response.
    """
    # Remove Tamil Unicode block (U+0B80–U+0BFF)
    text = re.sub(r'[\u0B80-\u0BFF]+', '', text)

    # Remove Sinhala Unicode block (U+0D80–U+0DFF)
    text = re.sub(r'[\u0D80-\u0DFF]+', '', text)

    # Remove any other non-ASCII characters except Rs symbol
    text = re.sub(r'[^\x00-\x7F\u20A8]+', '', text)

    # Clean up extra whitespace
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def _build_prompt(question: str, model: str) -> str:
    """
    Build model-specific prompt.
    Moondream: short and direct.
    Llava: detailed instructions.
    """
    question_lower = question.lower()

    asking_total   = any(w in question_lower for w in ["total", "pay", "amount", "payable", "bill"])
    asking_due     = any(w in question_lower for w in ["due", "date", "deadline", "when"])
    asking_account = any(w in question_lower for w in ["account", "number", "id"])
    asking_charges = any(w in question_lower for w in ["charge", "service", "breakdown", "detail"])
    asking_payment = any(w in question_lower for w in ["payment", "paid", "received"])

    english_rule = (
        "Reply in English only. "
        "No Tamil or Sinhala characters. "
        "Use only English words and numbers. "
    )

    if model.startswith("moondream"):
        if asking_total:
            return (
                f"{english_rule}"
                f"SLT Mobitel invoice. "
                f"What is the Total Payable amount in the summary table? "
                f"Answer: Rs. [number only]"
            )
        elif asking_due:
            return (
                f"{english_rule}"
                f"SLT Mobitel invoice. "
                f"What is the Payment Due Date? "
                f"Answer with date only."
            )
        elif asking_account:
            return (
                f"{english_rule}"
                f"SLT Mobitel invoice. "
                f"What is the Account Number at the top? "
                f"Answer with number only."
            )
        elif asking_charges:
            return (
                f"{english_rule}"
                f"SLT Mobitel invoice. "
                f"List all service charges with Rs. amounts. "
                f"One per line: Service: Rs. amount"
            )
        elif asking_payment:
            return (
                f"{english_rule}"
                f"SLT Mobitel invoice. "
                f"What payments were received? Amount and date only."
            )
        else:
            return (
                f"{english_rule}"
                f"SLT Mobitel invoice. {question} "
                f"English answer only. Be brief."
            )

    else:
        # Llava
        return (
            f"You are reading an SLT Mobitel bill.\n\n"
            f"RULE: Reply in ENGLISH ONLY. Ignore all Tamil and Sinhala text on the bill.\n\n"
            f"Question: '{question}'\n\n"
            f"Fields to look for:\n"
            f"- Account Number (top)\n"
            f"- Invoice Number\n"
            f"- Billing Date\n"
            f"- Bill Period\n"
            f"- Balance B/F\n"
            f"- Payments Received\n"
            f"- Arrears\n"
            f"- Charges for the period\n"
            f"- Total Payable (last column, summary table)\n"
            f"- Payment Due Date\n\n"
            f"Answer in English. Use Rs. for money amounts."
        )


def ask_image_question(image_file, question: str, model: str = "moondream") -> str:
    """
    Send image + question to Ollama vision model.
    """
    # Reset file pointer
    try:
        image_file.seek(0)
    except Exception:
        pass

    # Use smaller image for moondream to avoid timeout
    max_side = 800 if model.startswith("moondream") else 1400

    try:
        img_b64 = encode_image_to_base64(image_file, max_side=max_side)
    except Exception as e:
        return f"❌ Could not read image: {str(e)}"

    prompt = _build_prompt(question, model)

    # Token limit
    question_lower = question.lower()
    if any(w in question_lower for w in ["all", "list", "breakdown", "detail", "everything"]):
        num_predict = 300
    else:
        num_predict = 100

    payload = {
        "model":  model,
        "prompt": prompt,
        "images": [img_b64],
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": num_predict,
        }
    }

    # Moondream gets longer timeouts since it's slower on CPU
    if model.startswith("moondream"):
        timeouts = [180, 300]
    else:
        timeouts = [120, 200, 300]

    for attempt, t in enumerate(timeouts):
        try:
            print(f"[image_reader] Attempt {attempt + 1} — model: {model} — timeout: {t}s — image: {max_side}px")
            response = httpx.post(
                "http://localhost:11434/api/generate",
                json    = payload,
                timeout = httpx.Timeout(
                    connect = 15.0,
                    read    = float(t),
                    write   = 15.0,
                    pool    = 15.0,
                ),
            )
            response.raise_for_status()
            result = response.json().get("response", "").strip()

            if result:
                # Strip Tamil/Sinhala characters
                result = _clean_response(result)

                # Remove duplicate lines
                lines   = result.split("\n")
                seen    = set()
                cleaned = []
                for line in lines:
                    line = line.strip()
                    if line and line not in seen:
                        seen.add(line)
                        cleaned.append(line)

                final = "\n".join(cleaned)

                if len(final) < 5:
                    return (
                        "⚠️ Could not extract readable text from this image.\n\n"
                        "Try asking:\n"
                        "- 'What is the Total Payable amount?'\n"
                        "- 'What is the due date?'\n"
                        "- 'What is the account number?'"
                    )

                return final

        except httpx.TimeoutException:
            if attempt < len(timeouts) - 1:
                print(f"[image_reader] Timeout on attempt {attempt + 1}, retrying...")
                continue

            # Final timeout — give helpful advice
            return (
                "⏱️ Moondream is timing out on your computer.\n\n"
                "**This usually means your computer needs more RAM or CPU.**\n\n"
                "Try these fixes right now:\n"
                "1. Open Task Manager → close Chrome tabs and heavy apps\n"
                "2. Open terminal and restart Ollama:\n"
                "```\nollama stop moondream\nollama serve\n```\n"
                "3. Try again with a simpler question: 'What is the total?'\n\n"
                "If it keeps failing, switch to **llava** in the Vision model selector — "
                "it uses GPU acceleration which may be faster on your machine."
            )

        except httpx.ConnectError:
            return (
                "❌ Cannot connect to Ollama.\n\n"
                "Open a terminal and run:\n"
                "```\nollama serve\n```"
            )
        except httpx.HTTPStatusError as e:
            return f"❌ Ollama API error {e.response.status_code}: {e.response.text}"
        except Exception as e:
            return f"❌ Unexpected error: {str(e)}"

    return (
        "❌ Failed after all attempts.\n\n"
        "Please open terminal and run:\n"
        "```\nollama stop moondream\nollama serve\n```\n"
        "Then try again."
    )