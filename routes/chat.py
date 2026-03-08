import logging
import bleach
from flask import Blueprint, request, jsonify, session, current_app
from extensions import limiter

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a professional virtual health assistant for MedApp, a medical appointment booking platform in Nagpur, India.

Your role:
- Help users understand symptoms and suggest which type of doctor to consult
- Guide users through booking appointments on MedApp
- Provide general health tips and wellness advice
- Answer questions about our available doctors and hospitals

Rules:
- Never diagnose illnesses or prescribe medication
- Always recommend in-person consultation for serious symptoms
- Be empathetic, clear, and concise
- If a user describes an emergency, tell them to call emergency services (112 in India) immediately
- Keep responses under 150 words unless the topic really warrants more detail"""


def get_openai_client():
    api_key = current_app.config.get("OPENAI_API_KEY", "")
    if not api_key or api_key == "YOUR_OPENAI_KEY_HERE":
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception:
        return None


@chat_bp.route("/message", methods=["POST"])
@limiter.limit("30 per minute")
def message():
    data = request.get_json(silent=True) or {}
    raw_text = data.get("message", "").strip()

    if not raw_text:
        return jsonify({"reply": "Please type a message first."}), 400

    # Sanitize user input (strip all HTML tags)
    user_text = bleach.clean(raw_text, tags=[], strip=True)[:500]

    if not user_text:
        return jsonify({"reply": "Invalid message."}), 400

    # Maintain conversation history in session (last 10 turns = 20 messages)
    history = session.get("chat_history", [])
    history.append({"role": "user", "content": user_text})
    if len(history) > 20:
        history = history[-20:]

    client = get_openai_client()
    if client is None:
        session["chat_history"] = history
        reply = (
            "AI assistant is not configured yet. Please add your OpenAI API key to the .env file. "
            "In the meantime, you can browse our doctors and book an appointment directly!"
        )
        history.append({"role": "assistant", "content": reply})
        session["chat_history"] = history
        return jsonify({"reply": reply})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            max_tokens=200,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        history.append({"role": "assistant", "content": reply})
        session["chat_history"] = history
        session.modified = True
        return jsonify({"reply": reply})

    except Exception as e:
        logger.error("OpenAI error: %s", e)
        return jsonify({"reply": "Sorry, I'm having trouble connecting right now. Please try again in a moment."}), 200


@chat_bp.route("/reset", methods=["POST"])
def reset():
    session.pop("chat_history", None)
    return jsonify({"status": "ok"})
