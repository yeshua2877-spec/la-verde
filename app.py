import os
from flask import Flask, request, jsonify, send_from_directory
import anthropic
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv(override=True)

app = Flask(__name__)
CORS(app)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

sessions: dict[str, list[dict]] = {}

SYSTEM_PROMPT = """Sos el asistente virtual de LA VERDE, un emprendimiento de productos orgánicos.
Tu rol es atender a los clientes de manera cálida, cercana e informal. Sin formalismos.

Productos que vendemos:
- Yerba mate orgánica: de origen certificado, sin humo, sin aditivos.
- Azúcar mascabo orgánica: sin refinar, con todos sus nutrientes, sabor ahumado natural.
- Miel orgánica: pura, de abejas en entornos naturales, sin calor excesivo ni mezclas.
- Todo es de origen orgánico, sin agroquímicos ni procesos industriales.

Información importante:
- No manejamos precios fijos públicos. Para saber precios, el cliente tiene que consultar por WhatsApp.
- No hacemos envíos por el momento. La entrega es con retiro a coordinar.
- Contacto: WhatsApp +541158735921
- Si preguntan por stock o disponibilidad, deciles que consulten por WhatsApp.

Lineamientos:
- Hablá en español rioplatense (usá "vos", "te", "tu").
- Tono casual, amigable, humano. Como si hablaras con un conocido.
- Sé breve. Respuestas cortas y directas.
- Si te preguntan por precios, decí que por ahora los precios se consultan por WhatsApp (+541158735921).
- Si quieren comprar o encargar algo, mandá al WhatsApp.
- No inventes precios ni información que no tenés.
- Si no sabés algo, decilo con honestidad y derivá al WhatsApp.
"""

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 1024


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/widget.js")
def widget():
    return send_from_directory(".", "widget.js")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Se requiere un body JSON"}), 400

    message = data.get("message", "").strip()
    session_id = data.get("session_id", "").strip()

    if not message:
        return jsonify({"error": "El campo 'message' es requerido"}), 400
    if not session_id:
        return jsonify({"error": "El campo 'session_id' es requerido"}), 400

    history = sessions.setdefault(session_id, [])
    history.append({"role": "user", "content": message})

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=history,
        )
        assistant_text = response.content[0].text
    except anthropic.APIError as e:
        history.pop()
        return jsonify({"error": f"Error de API: {str(e)}"}), 500

    history.append({"role": "assistant", "content": assistant_text})

    return jsonify({
        "response": assistant_text,
        "session_id": session_id,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    })


@app.route("/chat/<session_id>", methods=["DELETE"])
def clear_session(session_id):
    sessions.pop(session_id, None)
    return jsonify({"message": f"Sesión '{session_id}' eliminada"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true", port=port)
