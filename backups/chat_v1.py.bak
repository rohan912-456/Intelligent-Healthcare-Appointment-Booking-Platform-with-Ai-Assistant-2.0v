import logging
import bleach
from flask import Blueprint, request, jsonify, session, current_app
from extensions import limiter

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a professional virtual health assistant for MedApp, "
    "a medical appointment booking platform in Nagpur, India.\n\n"
    "Your role:\n"
    "- Help users understand symptoms and suggest which type of doctor to consult\n"
    "- Guide users through booking appointments on MedApp\n"
    "- Provide general health tips and wellness advice\n"
    "- Answer questions about our available doctors and hospitals\n\n"
    "Rules:\n"
    "- Never diagnose illnesses or prescribe medication\n"
    "- Always recommend in-person consultation for serious symptoms\n"
    "- Be empathetic, clear, and concise\n"
    "- If a user describes an emergency, tell them to call emergency services "
    "(112 in India) immediately\n"
    "- Keep responses under 150 words unless the topic really warrants more detail"
)


def get_gemini_client():
    api_key = current_app.config.get("GEMINI_API_KEY", "")
    if not api_key or api_key == "YOUR_GEMINI_KEY_HERE":
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        # Using the specific version requested by the user and available in their key
        return genai.GenerativeModel("gemini-3.1-flash-lite-preview")
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

    # Maintain conversation history in session
    # Format: {"role": "user"/"assistant", "content": "..."}
    history = session.get("chat_history", [])
    history.append({"role": "user", "content": user_text})
    if len(history) > 20:
        history = history[-20:]

    model = get_gemini_client()
    if model is None:
        session["chat_history"] = history
        reply = (
            "AI assistant is not configured yet. Please add your GEMINI_API_KEY to the .env file. "
            "In the meantime, you can browse our doctors and book an appointment directly!"
        )
        history.append({"role": "assistant", "content": reply})
        session["chat_history"] = history
        return jsonify({"reply": reply})

    try:
        # Map existing history to Gemini format (role: user/model, parts: [str])
        gemini_history = []
        # System prompt as the very first message if history is empty or as context
        # In Gemini 1.5, we can use system_instruction in the model constructor
        # but here we'll just prepend it or use a simplified approach

        for turn in history[:-1]:  # All except the current message
            role = "user" if turn["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [turn["content"]]})

        # Re-initialize model with system instruction
        import google.generativeai as genai
        model = genai.GenerativeModel(
            model_name="gemini-3.1-flash-lite-preview",
            system_instruction=SYSTEM_PROMPT
        )

        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(user_text)

        reply = response.text.strip()
        history.append({"role": "assistant", "content": reply})
        session["chat_history"] = history
        session.modified = True
        return jsonify({"reply": reply})

    except Exception as e:
        logger.error("Gemini error: %s", e)
        return jsonify({"reply": "Sorry, I'm having trouble connecting right now. Please try again in a moment."}), 200


@chat_bp.route("/reset", methods=["POST"])
def reset():
    session.pop("chat_history", None)
    return jsonify({"status": "ok"})
