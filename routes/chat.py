import logging
import bleach
from flask import Blueprint, request, jsonify, session, current_app
from extensions import limiter

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a professional virtual health assistant for Clinical Couture, "
    "a medical appointment booking platform in Nagpur, India.\n\n"
    "Your role:\n"
    "- Help users understand symptoms and suggest which type of doctor to consult\n"
    "- Guide users through booking appointments on Clinical Couture\n"
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


# ── Keyword Mapping for Digital Intake ──────────────────────
SYMPTOM_MAP = {
    "cardiologist": ["heart", "chest pain", "pulse", "hypertension", "palpitation", "cardiac"],
    "dermatologist": ["skin", "rash", "acne", "itch", "dermal", "eczema", "burn"],
    "pediatrician": ["child", "baby", "infant", "toddler", "pediatric"],
    "orthopedic surgeon": ["bone", "joint", "fracture", "spine", "knee", "ortho", "back pain"],
    "neurologist": ["brain", "headache", "migraine", "seizure", "stroke", "nerve"],
    "pulmonologist": ["breath", "lung", "asthma", "cough", "shortness of breath", "呼吸"],
    "psychiatrist": ["anxiety", "depression", "sleep", "stress", "mental", "behavior"],
    "general physician": ["fever", "cold", "body pain", "flu", "weakness", "infection", "checkup"]
}

@chat_bp.route("/message", methods=["POST"])
@limiter.limit("60 per minute")
def message():
    from models import Doctor
    data = request.get_json(silent=True) or {}
    raw_text = data.get("message", "").strip()

    if not raw_text:
        return jsonify({"reply": "Please type a message first."}), 400

    user_text = bleach.clean(raw_text, tags=[], strip=True)[:500]
    user_query = user_text.lower()

    # ── History Synchronization ──
    # Initialize history early so LOCAL matches are recorded
    history = session.get("chat_history", [])
    history.append({"role": "user", "content": user_text})
    if len(history) > 10:
        history = history[-10:]

    # 1. Handle Affirmative Intent (Success Follow-up)
    AFFIRMATIVE_KEYWORDS = ["yes", "yeah", "sure", "book", "help", "proceed", "okay", "ok"]
    pending_specialist_id = session.get("pending_specialist_id")
    if any(kw == user_query for kw in AFFIRMATIVE_KEYWORDS) and pending_specialist_id:
        doctor = Doctor.query.get(pending_specialist_id)
        if doctor:
            reply = (
                f"Excellent choice. I'm ready to facilitate your protocol at {doctor.hospital}. "
                f"Please use the booking interface below to secure your slot with {doctor.name}."
            )
            history.append({"role": "assistant", "content": reply})
            session["chat_history"] = history
            session.modified = True
            return jsonify({
                "reply": reply,
                "specialist": {
                    "id": doctor.id, "name": doctor.name,
                    "specialty": doctor.specialty, "hospital": doctor.hospital
                }
            })

    # 2. Local Keyword Matching (Digital Intake)
    matched_specialty = None
    for specialty, keywords in SYMPTOM_MAP.items():
        if any(kw in user_query for kw in keywords):
            matched_specialty = specialty
            break

    if matched_specialty:
        doctor = Doctor.query.filter(Doctor.specialty.ilike(f"%{matched_specialty}%")).filter_by(available=True).first()
        if doctor:
            # Store for affirmative follow-up
            session["pending_specialist_id"] = doctor.id
            reply = (
                f"Based on your symptoms, I recommend a consultation with a {doctor.specialty.title()}. "
                f"{doctor.name} at {doctor.hospital} is available. Would you like me to help you book this?"
            )
            history.append({"role": "assistant", "content": reply})
            session["chat_history"] = history
            session.modified = True
            return jsonify({
                "reply": reply,
                "specialist": {
                    "id": doctor.id, "name": doctor.name,
                    "specialty": doctor.specialty, "hospital": doctor.hospital
                }
            })

    # 3. Fallback to Gemini (AI Analysis)
    session.pop("pending_specialist_id", None)  # Clear pending if we move to general chat
    model = get_gemini_client()
    if model is None:
        reply = (
            "I'm currently in high-speed triage mode. Describe symptoms like "
            "'headache' or 'chest pain' for a specialist referral."
        )
        history.append({"role": "assistant", "content": reply})
        session["chat_history"] = history
        return jsonify({"reply": reply})

    try:
        # Prepend System Prompt to the actual generation call for better context
        full_context_prompt = f"System Instruction: {SYSTEM_PROMPT}\n\nRecent History:\n"
        for h in history[:-1]:
            full_context_prompt += f"{h['role'].capitalize()}: {h['content']}\n"
        full_context_prompt += f"User: {user_text}\nAssistant:"

        response = model.generate_content(
            full_context_prompt,
            generation_config={"max_output_tokens": 150, "temperature": 0.7}
        )

        reply = response.text.strip()
        history.append({"role": "assistant", "content": reply})
        session["chat_history"] = history
        session.modified = True
        return jsonify({"reply": reply})

    except Exception as e:
        logger.error("Gemini error: %s", e)
        return jsonify({
            "reply": "I'm experiencing a brief latency in clinical data. "
                     "Could you rephrase your symptoms?"
        }), 200


@chat_bp.route("/reset", methods=["POST"])
def reset():
    session.pop("chat_history", None)
    return jsonify({"status": "ok"})
