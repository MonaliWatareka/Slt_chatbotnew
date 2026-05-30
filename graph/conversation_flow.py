"""
graph/conversation_flow.py
Handles guided multi-turn conversations for SLT package recommendations.
When a user asks about packages, the bot asks questions step by step
and then gives a personalized recommendation.
"""

# ─────────────────────────────────────────────────────────────────────────────
# All guided flows defined here
# Each flow has:
#   - trigger_keywords: what user says to start this flow
#   - steps: list of questions to ask one by one
#   - final_handler: function that takes all answers and returns recommendation
# ─────────────────────────────────────────────────────────────────────────────

FLOWS = {

    "fiber_package": {
        "trigger_keywords": [
            "select fiber", "choose fiber", "which fiber", "fiber package",
            "best fiber", "recommend fiber", "fiber plan", "broadband package",
            "which package", "what package", "suggest package", "fiber internet",
            "home fiber", "home broadband"
        ],
        "intro": "I'll help you find the best SLT Fiber package! Let me ask you a few quick questions. 😊",
        "steps": [
            {
                "key":      "members",
                "question": "👨‍👩‍👧‍👦 How many people are in your household who will use the internet?",
                "type":     "number",
                "hint":     "e.g. 1, 3, 5"
            },
            {
                "key":      "usage",
                "question": "💻 What do you mainly use the internet for?\n\n"
                            "1. Basic browsing & social media\n"
                            "2. Video streaming (YouTube, Netflix)\n"
                            "3. Online gaming\n"
                            "4. Work from home / video calls\n"
                            "5. All of the above\n\n"
                            "Reply with a number (1-5):",
                "type":     "choice",
                "hint":     "Reply 1, 2, 3, 4 or 5"
            },
            {
                "key":      "budget",
                "question": "💰 What is your monthly budget for internet? (in Rs.)\n\n"
                            "1. Under Rs. 2,000\n"
                            "2. Rs. 2,000 – Rs. 4,000\n"
                            "3. Rs. 4,000 – Rs. 7,000\n"
                            "4. Above Rs. 7,000\n\n"
                            "Reply with a number (1-4):",
                "type":     "choice",
                "hint":     "Reply 1, 2, 3 or 4"
            },
            {
                "key":      "peotv",
                "question": "📺 Are you interested in adding **SLT PeoTV** (cable TV service)?",
                "type":     "yes_no",
                "hint":     "Reply Yes or No"
            },
        ],
        "final_handler": "_recommend_fiber_package"
    },

    "peotv_package": {
        "trigger_keywords": [
            "peotv", "peo tv", "tv package", "select tv", "choose tv",
            "which tv package", "best tv package", "recommend tv",
            "cable tv", "iptv"
        ],
        "intro": "I'll help you pick the right SLT PeoTV package! 📺 Just a few questions:",
        "steps": [
            {
                "key":      "viewers",
                "question": "👨‍👩‍👧 How many people will be watching TV regularly?",
                "type":     "number",
                "hint":     "e.g. 2, 4"
            },
            {
                "key":      "content",
                "question": "🎬 What type of content do you prefer?\n\n"
                            "1. Local Sri Lankan channels only\n"
                            "2. International channels (HBO, Discovery etc.)\n"
                            "3. Sports channels\n"
                            "4. Kids & family channels\n"
                            "5. Mix of everything\n\n"
                            "Reply with a number (1-5):",
                "type":     "choice",
                "hint":     "Reply 1, 2, 3, 4 or 5"
            },
            {
                "key":      "budget",
                "question": "💰 What is your monthly budget for TV?\n\n"
                            "1. Under Rs. 1,000\n"
                            "2. Rs. 1,000 – Rs. 2,500\n"
                            "3. Above Rs. 2,500\n\n"
                            "Reply with a number (1-3):",
                "type":     "choice",
                "hint":     "Reply 1, 2 or 3"
            },
        ],
        "final_handler": "_recommend_peotv_package"
    },

    "mobile_package": {
        "trigger_keywords": [
            "mobitel", "mobile package", "sim package", "mobile data",
            "prepaid", "postpaid", "mobile plan", "4g package",
            "which sim", "best mobile"
        ],
        "intro": "Let me help you find the best Mobitel package! 📱 Quick questions:",
        "steps": [
            {
                "key":      "type",
                "question": "📋 Do you prefer Prepaid or Postpaid?\n\n"
                            "1. Prepaid (pay as you go)\n"
                            "2. Postpaid (monthly bill)\n\n"
                            "Reply 1 or 2:",
                "type":     "choice",
                "hint":     "Reply 1 or 2"
            },
            {
                "key":      "data",
                "question": "📶 How much mobile data do you use per month?\n\n"
                            "1. Light (under 5GB)\n"
                            "2. Medium (5GB – 15GB)\n"
                            "3. Heavy (15GB – 30GB)\n"
                            "4. Very heavy (30GB+)\n\n"
                            "Reply 1, 2, 3 or 4:",
                "type":     "choice",
                "hint":     "Reply 1, 2, 3 or 4"
            },
            {
                "key":      "calls",
                "question": "📞 Do you make a lot of voice calls?",
                "type":     "yes_no",
                "hint":     "Reply Yes or No"
            },
            {
                "key":      "budget",
                "question": "💰 Monthly budget for mobile?\n\n"
                            "1. Under Rs. 500\n"
                            "2. Rs. 500 – Rs. 1,500\n"
                            "3. Rs. 1,500 – Rs. 3,000\n"
                            "4. Above Rs. 3,000\n\n"
                            "Reply 1, 2, 3 or 4:",
                "type":     "choice",
                "hint":     "Reply 1, 2, 3 or 4"
            },
        ],
        "final_handler": "_recommend_mobile_package"
    },

    "bill_query": {
        "trigger_keywords": [
            "understand my bill", "explain my bill", "bill too high",
            "why is my bill", "bill increased", "high bill", "bill problem"
        ],
        "intro": "I'll help you understand your SLT bill! Let me ask a few things:",
        "steps": [
            {
                "key":      "services",
                "question": "📋 Which SLT services do you currently have?\n\n"
                            "1. Fiber internet only\n"
                            "2. Fiber + PeoTV\n"
                            "3. Fiber + Mobile\n"
                            "4. All services\n\n"
                            "Reply 1, 2, 3 or 4:",
                "type":     "choice",
                "hint":     "Reply 1, 2, 3 or 4"
            },
            {
                "key":      "issue",
                "question": "❓ What is the issue with your bill?\n\n"
                            "1. Bill is higher than usual\n"
                            "2. I don't understand the charges\n"
                            "3. I was charged for something I didn't use\n"
                            "4. I want to reduce my bill\n\n"
                            "Reply 1, 2, 3 or 4:",
                "type":     "choice",
                "hint":     "Reply 1, 2, 3 or 4"
            },
        ],
        "final_handler": "_recommend_bill_help"
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Flow detection — checks if a message triggers a guided flow
# ─────────────────────────────────────────────────────────────────────────────

def detect_flow(user_input: str) -> str | None:
    """Returns flow name if user message triggers a guided flow, else None."""
    text = user_input.lower().strip()
    for flow_name, flow_data in FLOWS.items():
        for keyword in flow_data["trigger_keywords"]:
            if keyword in text:
                return flow_name
    return None


def get_flow(flow_name: str) -> dict:
    """Returns flow definition dict."""
    return FLOWS.get(flow_name, {})


# ─────────────────────────────────────────────────────────────────────────────
# Step manager — returns next question or final recommendation
# ─────────────────────────────────────────────────────────────────────────────

def get_next_step(flow_name: str, answers: dict) -> dict | None:
    """
    Returns the next unanswered step dict, or None if all steps done.
    """
    flow  = get_flow(flow_name)
    steps = flow.get("steps", [])
    for step in steps:
        if step["key"] not in answers:
            return step
    return None  # all steps answered


def is_flow_complete(flow_name: str, answers: dict) -> bool:
    """Returns True if all steps have been answered."""
    flow  = get_flow(flow_name)
    steps = flow.get("steps", [])
    return all(step["key"] in answers for step in steps)


# ─────────────────────────────────────────────────────────────────────────────
# Final recommendation handlers
# ─────────────────────────────────────────────────────────────────────────────

def generate_recommendation(flow_name: str, answers: dict) -> str:
    """Calls the correct recommendation function based on flow name."""
    handlers = {
        "fiber_package":  _recommend_fiber_package,
        "peotv_package":  _recommend_peotv_package,
        "mobile_package": _recommend_mobile_package,
        "bill_query":     _recommend_bill_help,
    }
    handler = handlers.get(flow_name)
    if handler:
        return handler(answers)
    return "✅ Thank you! Please contact SLT on **1212** for personalized assistance."


def _recommend_fiber_package(answers: dict) -> str:
    members = answers.get("members", "").strip()
    usage   = answers.get("usage", "1")
    budget  = answers.get("budget", "2")
    peotv   = answers.get("peotv", "no").lower()

    # Parse members
    try:
        member_count = int(''.join(filter(str.isdigit, members)))
    except Exception:
        member_count = 3

    # Recommendation logic
    if budget == "1" or member_count <= 2:
        package = {
            "name":    "SLT Fiber 25 Mbps — Basic",
            "speed":   "25 Mbps",
            "price":   "Rs. 1,799/month",
            "data":    "Unlimited",
            "reason":  "Perfect for light users or small households"
        }
    elif budget == "2" or member_count <= 3:
        package = {
            "name":    "SLT Fiber 50 Mbps — Standard",
            "speed":   "50 Mbps",
            "price":   "Rs. 2,999/month",
            "data":    "Unlimited",
            "reason":  "Great for streaming and working from home"
        }
    elif budget == "3" or member_count <= 5:
        package = {
            "name":    "SLT Fiber 100 Mbps — Plus",
            "speed":   "100 Mbps",
            "price":   "Rs. 4,999/month",
            "data":    "Unlimited",
            "reason":  "Ideal for large families with multiple devices"
        }
    else:
        package = {
            "name":    "SLT Fiber 200 Mbps — Premium",
            "speed":   "200 Mbps",
            "price":   "Rs. 6,999/month",
            "data":    "Unlimited",
            "reason":  "Best for heavy users, gamers, and large households"
        }

    usage_labels = {
        "1": "Basic browsing & social media",
        "2": "Video streaming",
        "3": "Online gaming",
        "4": "Work from home",
        "5": "All purposes"
    }

    peotv_note = (
        "\n\n📺 **PeoTV Add-on:** Since you're interested in PeoTV, "
        "ask about the **Fiber + PeoTV bundle** for a discounted combined rate!"
        if "yes" in peotv else ""
    )

    return f"""✅ **Based on your answers, here is my recommendation:**

---

### 🌐 {package['name']}
| Detail | Info |
|--------|------|
| **Speed** | {package['speed']} |
| **Monthly Price** | {package['price']} |
| **Data** | {package['data']} |
| **Household Size** | {member_count} people |
| **Main Usage** | {usage_labels.get(usage, 'General use')} |

**Why this package?** {package['reason']}{peotv_note}

---

📞 **To subscribe:** Call **1212** or visit **https://myslt.slt.lk**
🏪 Or visit your nearest SLT Customer Care Centre

*Would you like to know more about this package or compare with others?*"""


def _recommend_peotv_package(answers: dict) -> str:
    viewers = answers.get("viewers", "2")
    content = answers.get("content", "1")
    budget  = answers.get("budget", "2")

    if budget == "1":
        package = {
            "name":     "PeoTV Basic",
            "channels": "80+ channels",
            "price":    "Rs. 799/month",
            "includes": "Local + basic international"
        }
    elif budget == "2":
        package = {
            "name":     "PeoTV Standard",
            "channels": "130+ channels",
            "price":    "Rs. 1,499/month",
            "includes": "Local + international + sports"
        }
    else:
        package = {
            "name":     "PeoTV Premium",
            "channels": "180+ channels",
            "price":    "Rs. 2,499/month",
            "includes": "All channels including HBO, Discovery, sports, kids"
        }

    content_labels = {
        "1": "Local channels",
        "2": "International channels",
        "3": "Sports",
        "4": "Kids & family",
        "5": "Mix of everything"
    }

    return f"""✅ **Here is your PeoTV recommendation:**

---

### 📺 {package['name']}
| Detail | Info |
|--------|------|
| **Channels** | {package['channels']} |
| **Monthly Price** | {package['price']} |
| **Includes** | {package['includes']} |
| **Content Interest** | {content_labels.get(content, 'General')} |

---

📞 **To subscribe:** Call **1212** or visit **https://myslt.slt.lk**

*Want to bundle this with your SLT Fiber for a discount?*"""


def _recommend_mobile_package(answers: dict) -> str:
    plan_type = answers.get("type", "1")
    data      = answers.get("data", "2")
    calls     = answers.get("calls", "no").lower()
    budget    = answers.get("budget", "2")

    is_prepaid = plan_type == "1"

    if is_prepaid:
        if data in ["1", "2"]:
            package = {
                "name":  "Mobitel Prepaid — Smart Pack",
                "data":  "8GB",
                "price": "Rs. 299 (7 days)",
                "calls": "50 mins local calls included"
            }
        else:
            package = {
                "name":  "Mobitel Prepaid — Super Pack",
                "data":  "25GB",
                "price": "Rs. 699 (30 days)",
                "calls": "100 mins local calls included"
            }
    else:
        if budget in ["1", "2"]:
            package = {
                "name":  "Mobitel Postpaid — Value Plan",
                "data":  "15GB",
                "price": "Rs. 999/month",
                "calls": "Unlimited on-net calls"
            }
        else:
            package = {
                "name":  "Mobitel Postpaid — Premium Plan",
                "data":  "50GB",
                "price": "Rs. 2,499/month",
                "calls": "Unlimited all-network calls"
            }

    calls_note = (
        "\n💡 **Tip:** Since you make many calls, consider adding a **Voice Add-on** for extra savings!"
        if "yes" in calls else ""
    )

    return f"""✅ **Here is your Mobitel recommendation:**

---

### 📱 {package['name']}
| Detail | Info |
|--------|------|
| **Data** | {package['data']} |
| **Price** | {package['price']} |
| **Calls** | {package['calls']} |
| **Type** | {'Prepaid' if is_prepaid else 'Postpaid'} |
{calls_note}

---

📞 **To activate:** Call **1717** or visit **https://www.mobitel.lk**
🏪 Or visit nearest Mobitel outlet

*Need help comparing more plans?*"""


def _recommend_bill_help(answers: dict) -> str:
    services = answers.get("services", "1")
    issue    = answers.get("issue", "1")

    responses = {
        "1": (
            "📈 **Bill Higher Than Usual?**\n\n"
            "Common reasons:\n"
            "- Extra data usage (videos, downloads)\n"
            "- New service or add-on activated\n"
            "- Annual price revision\n"
            "- Arrears from previous month\n\n"
            "**What to do:**\n"
            "1. Upload your bill image here and ask me to break it down\n"
            "2. Check usage at **https://myslt.slt.lk**\n"
            "3. Call **1212** to dispute any charge"
        ),
        "2": (
            "📋 **Understanding Your Charges:**\n\n"
            "Your SLT bill has these sections:\n"
            "- **Balance B/F** — amount carried from last month\n"
            "- **Payments Received** — what you already paid\n"
            "- **Arrears** — remaining unpaid balance\n"
            "- **Charges for Period** — this month's new charges\n"
            "- **Total Payable** — what you must pay now\n\n"
            "💡 Upload your bill image and ask me specific questions!"
        ),
        "3": (
            "⚠️ **Charged for Something You Didn't Use?**\n\n"
            "**Steps to dispute:**\n"
            "1. Call SLT hotline: **1212** (24/7)\n"
            "2. Visit: **https://myslt.slt.lk** → Complaints\n"
            "3. Visit nearest SLT Customer Care Centre\n\n"
            "Have your **Account Number** and **Invoice Number** ready."
        ),
        "4": (
            "💡 **Ways to Reduce Your SLT Bill:**\n\n"
            "1. Downgrade to a lower speed package\n"
            "2. Remove unused add-ons (PeoTV, extra GB)\n"
            "3. Monitor data usage on MySLT app\n"
            "4. Ask about **bundle discounts** (Fiber + PeoTV)\n"
            "5. Pay on time to avoid late fees\n\n"
            "📞 Call **1212** to review your current plan"
        ),
    }

    return responses.get(issue, responses["2"]) + "\n\n*Is there anything else I can help you with?*"