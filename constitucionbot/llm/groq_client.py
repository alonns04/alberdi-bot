import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from config import MAX_QUESTION_CHARS, MAX_TOKENS, MODEL_GROQ, TEMPERATURE
from history.manager import load_history as load_chat_history


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompt_de_entrada" / "prompt.txt"


def load_initial_prompt() -> str:
    if not PROMPT_PATH.exists():
        return "Responde según el contexto provisto."

    with PROMPT_PATH.open("r", encoding="utf-8") as file:
        return file.read()


def load_history(user_id: str | None = None):
    return load_chat_history(user_id=user_id)


def validate_model(client: Groq) -> None:
    available_models = {model.id for model in client.models.list().data}
    if MODEL_GROQ not in available_models:
        raise ValueError(
            f"El modelo Groq configurado no está disponible: {MODEL_GROQ}. "
            "Configura MODEL_GROQ con un modelo habilitado en tu cuenta."
        )


def ask(
    question: str,
    context: str,
    user_id: str | None = None,
    api_key: str | None = None,
) -> str:
    if len(question) > MAX_QUESTION_CHARS:
        return "No podemos procesar tu mensaje porque supera el límite de longitud permitido."

    resolved_api_key = api_key or os.getenv("API_KEY_GROQ")
    if not resolved_api_key:
        return "No se pudo contactar a Groq porque no está configurada la variable API_KEY_GROQ."

    client = Groq(api_key=resolved_api_key)
    prompt_inicial = load_initial_prompt()
    historial = load_history(user_id=user_id)

    messages = [{"role": "system", "content": prompt_inicial}]
    messages.extend(historial)
    messages.append(
        {
            "role": "user",
            "content": f"""Contexto documental:
{context or 'No se encontró contexto relevante en la base documental.'}

Pregunta:
{question}""",
        }
    )

    print("[Historial enviado a la IA]")
    for idx, message in enumerate(messages, start=1):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        print(f"[{idx}] {role}: {content}")
    print("[Fin historial]")

    try:
        validate_model(client)
        response = client.chat.completions.create(
            model=MODEL_GROQ,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        return response.choices[0].message.content
    except Exception as exc:
        error_body = getattr(exc, "body", {}) or {}
        error_data = error_body.get("error", {}) if isinstance(error_body, dict) else {}
        if getattr(exc, "status_code", None) == 401 or error_data.get("code") == "invalid_api_key":
            raise RuntimeError("INVALID_API_KEY") from exc
        return f"No se pudo completar la consulta con Groq: {exc}"