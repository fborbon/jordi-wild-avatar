"""
Jordi Wild interview avatar.
Loads the style profile and conducts an interview in his style.

Usage:
  python avatar/jordi_avatar.py
  python avatar/jordi_avatar.py --topic "inteligencia artificial"

Requires: ANTHROPIC_API_KEY env var, ./data/jordi_style_profile.json
"""

import json
import os
import argparse
import anthropic
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
if os.path.exists(dotenv_path):
    with open(dotenv_path) as _f:
        for _line in _f:
            if "=" in _line and not _line.startswith("#"):
                _k, _v = _line.strip().split("=", 1)
                os.environ.setdefault(_k, _v)

PROFILE_PATH = "./data/jordi_style_profile.json"
client = anthropic.Anthropic()


def load_profile() -> dict:
    if not os.path.exists(PROFILE_PATH):
        print(f"Style profile not found at {PROFILE_PATH}.")
        print("Run 03_extract_style.py first, or use the avatar with default personality.")
        return {}
    with open(PROFILE_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(profile: dict, topic: str) -> str:
    if not profile:
        return (
            "Eres Jordi Wild, presentador del podcast The Wild Project. "
            "Entrevistas a invitados con un estilo directo, curioso, a veces irreverente, "
            "con sentido del humor y sin miedo a hacer preguntas incómodas. "
            "Hablas en español coloquial. Haz preguntas de una en una y reacciona a las respuestas."
        )

    vocab = ", ".join(profile.get("vocabulary", [])[:15])
    reactions = ", ".join(profile.get("reactions", [])[:10])
    traits = ", ".join(profile.get("personality_traits", []))
    samples = "\n".join(f'  - "{q}"' for q in profile.get("sample_questions", [])[:6])
    humor = profile.get("humor_style", "")
    tone = profile.get("tone_description", "")
    transitions = ", ".join(profile.get("topic_transitions", [])[:5])

    return f"""Eres Jordi Wild, presentador de The Wild Project, uno de los podcasts más conocidos en español.

ESTILO Y PERSONALIDAD:
- Tono: {tone}
- Rasgos: {traits}
- Humor: {humor}

VOCABULARIO CARACTERÍSTICO (úsalo naturalmente):
{vocab}

REACCIONES TÍPICAS (intercálalas):
{reactions}

TRANSICIONES DE TEMA:
{transitions}

MUESTRA DE PREGUNTAS REPRESENTATIVAS (como referencia de estilo, no para repetir literalmente):
{samples}

REGLAS DE CONDUCTA:
- Haz UNA sola pregunta por turno, espera la respuesta y reacciona antes de preguntar lo siguiente.
- Reacciona genuinamente a las respuestas: sorpresa, acuerdo, cuestionamiento, humor.
- Si el invitado dice algo interesante, explóralo antes de cambiar de tema.
- No eres un chatbot genérico. Eres Jordi. Habla como él, no como un asistente.
- Usa lenguaje coloquial español, no latinoamericano.
- El tema de la entrevista de hoy: {topic}

Empieza saludando al invitado como lo haría Jordi y lanzando la primera pregunta."""


def run_interview(topic: str = "lo que el invitado quiera compartir"):
    profile = load_profile()
    system_prompt = build_system_prompt(profile, topic)

    print("\n" + "="*60)
    print("  THE WILD PROJECT — Avatar de Jordi Wild")
    print("  (escribe 'salir' para terminar)")
    print("="*60 + "\n")

    history = []

    # Jordi opens
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": "[El invitado entra al estudio y se sienta.]"}],
    )
    jordi_opening = response.content[0].text
    history.append({"role": "user", "content": "[El invitado entra al estudio y se sienta.]"})
    history.append({"role": "assistant", "content": jordi_opening})
    print(f"Jordi: {jordi_opening}\n")

    while True:
        user_input = input("Tú: ").strip()
        if not user_input or user_input.lower() in ("salir", "exit", "quit"):
            print("\nJordi: Bueno, ha sido un placer. ¡Nos vemos!")
            break

        history.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=system_prompt,
            messages=history,
        )
        jordi_reply = response.content[0].text
        history.append({"role": "assistant", "content": jordi_reply})
        print(f"\nJordi: {jordi_reply}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jordi Wild interview avatar")
    parser.add_argument("--topic", default="tu vida y experiencias", help="Topic of the interview")
    args = parser.parse_args()
    run_interview(topic=args.topic)
