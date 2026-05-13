"""
THE WILD PROJECT — Jordi Wild Avatar Launcher

Modes:
  chatbot   Text conversation (keyboard in, text out)
  callLQ    Voice call — lightweight (edge-tts, fast, needs internet)
  callHQ    Voice call — high quality (XTTS v2 local ~1.8GB, slow without GPU)
  videocall Animated face + voice (edge-tts + MediaPipe face animation)

Usage:
  python3 jordi.py                          # interactive menu
  python3 jordi.py --mode chatbot           # skip menu
  python3 jordi.py --mode videocall --topic "IA y el futuro"
  python3 jordi.py --mode videocall --photo jordi_cartoon.png
"""

import os, sys, argparse, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))

MODES = {
    "1": "chatbot",
    "2": "callLQ",
    "3": "callHQ",
    "4": "videocall",
}

MODE_INFO = {
    "chatbot": {
        "label":   "Chatbot — solo texto",
        "desc":    "Conversación por teclado. Sin audio. Rápido, sin requisitos extra.",
        "warning": None,
    },
    "callLQ": {
        "label":   "CallLQ — llamada de voz ligera",
        "desc":    "Micrófono → Whisper → Claude → edge-tts (voz genérica). Rápido, necesita internet.",
        "warning": None,
    },
    "callHQ": {
        "label":   "CallHQ — llamada de voz alta calidad",
        "desc":    "Igual que callLQ pero usa XTTS v2 local (~1.8 GB) para clonar la voz de Jordi.",
        "warning": "AVISO: Síntesis lenta en CPU (~20-30s/respuesta). Recomendado GPU.",
    },
    "videocall": {
        "label":   "Videollamada — avatar animado",
        "desc":    "Cara animada de Jordi (boca, ojos, cabeza) sincronizada con su voz. Necesita foto.",
        "warning": "AVISO: Requiere hardware moderado. En CPU puede ir a 10-15 fps.",
    },
}

DEFAULT_PHOTO = os.path.join(BASE, "jordi_cartoon.png")
if not os.path.exists(DEFAULT_PHOTO):
    DEFAULT_PHOTO = os.path.join(BASE, "jordi.jpeg")


def print_banner():
    print("\n" + "═"*58)
    print("   ████████╗██╗    ██╗██████╗ ")
    print("      ██╔══╝██║    ██║██╔══██╗")
    print("      ██║   ██║ █╗ ██║██████╔╝")
    print("      ██║   ██║███╗██║██╔═══╝ ")
    print("      ██║   ╚███╔███╔╝██║     ")
    print("      ╚═╝    ╚══╝╚══╝ ╚═╝     ")
    print("   THE WILD PROJECT — Avatar de Jordi Wild")
    print("═"*58 + "\n")


def select_mode() -> str:
    print("Elige el modo de interacción:\n")
    for k, mode in MODES.items():
        info = MODE_INFO[mode]
        print(f"  {k}. {info['label']}")
        print(f"     {info['desc']}")
        if info["warning"]:
            print(f"     ⚠  {info['warning']}")
        print()
    while True:
        choice = input("Selecciona [1-4]: ").strip()
        if choice in MODES:
            return MODES[choice]
        print("  Opción inválida. Escribe 1, 2, 3 o 4.")


def select_topic() -> str:
    topic = input("Tema de la entrevista (Enter = libre): ").strip()
    return topic if topic else "lo que quieras hablar"


def select_photo() -> str:
    if os.path.exists(DEFAULT_PHOTO):
        use = input(f"Usar foto por defecto ({os.path.basename(DEFAULT_PHOTO)})? [S/n]: ").strip().lower()
        if use in ("", "s", "y", "si", "yes"):
            return DEFAULT_PHOTO
    path = input("Ruta a la foto: ").strip()
    return path if path else DEFAULT_PHOTO


def launch(mode: str, topic: str, photo: str | None):
    info = MODE_INFO[mode]
    print(f"\nIniciando modo: {info['label']}")
    if info["warning"]:
        print(f"⚠  {info['warning']}")
    print()

    env = os.environ.copy()

    if mode == "chatbot":
        subprocess.run(
            [sys.executable, os.path.join(BASE, "avatar", "jordi_chat.py"),
             "--topic", topic],
            env=env,
        )

    elif mode == "callLQ":
        cmd = [sys.executable, os.path.join(BASE, "avatar", "jordi_avatar_voice.py"),
               "--topic", topic, "--tts", "edge"]
        if photo:
            cmd += ["--photo", photo]
        subprocess.run(cmd, env=env)

    elif mode == "callHQ":
        cmd = [sys.executable, os.path.join(BASE, "avatar", "jordi_avatar_voice.py"),
               "--topic", topic, "--tts", "xtts"]
        if photo:
            cmd += ["--photo", photo]
        subprocess.run(cmd, env=env)

    elif mode == "videocall":
        photo = photo or DEFAULT_PHOTO
        cmd = [sys.executable, os.path.join(BASE, "avatar", "jordi_avatar_voice.py"),
               "--topic", topic, "--tts", "edge", "--photo", photo]
        subprocess.run(cmd, env=env)


def main():
    parser = argparse.ArgumentParser(description="Jordi Wild Avatar Launcher")
    parser.add_argument("--mode",  choices=list(MODES.values()), default=None)
    parser.add_argument("--topic", default=None)
    parser.add_argument("--photo", default=None)
    args = parser.parse_args()

    print_banner()

    mode  = args.mode  or select_mode()
    topic = args.topic or select_topic()
    photo = args.photo

    if mode in ("callLQ", "callHQ", "videocall") and photo is None:
        if mode == "videocall":
            photo = select_photo()
        elif os.path.exists(DEFAULT_PHOTO):
            photo = DEFAULT_PHOTO

    launch(mode, topic, photo)


if __name__ == "__main__":
    main()
