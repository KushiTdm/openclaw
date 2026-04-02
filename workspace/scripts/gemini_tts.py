#!/home/ubuntu/.local/bin/python3-anna
"""
Gemini TTS — Remplacement ElevenLabs pour Anna / NeuraWeb
Génère un fichier WAV depuis Gemini 2.5 Flash TTS, puis le convertit en OGG Opus pour WhatsApp.

Usage:
  python3 gemini_tts.py "Texte à dire" /tmp/output.ogg
  python3 gemini_tts.py "Texte à dire" /tmp/output.ogg --lang es
  python3 gemini_tts.py "Texte à dire" /tmp/output.ogg --voice Zephyr

Prérequis:
  pip install google-genai
  export GEMINI_API_KEY="votre_clé"
  ffmpeg installé sur le système
"""

import os
import sys
import struct
import mimetypes
import subprocess
import tempfile
from google import genai
from google.genai import types

# Voix disponibles dans Gemini TTS (au 2026-03)
# Choisir selon le contexte : Anna parle espagnol (prospectos) ou français (Nacer)
VOICES = {
    "Zephyr":   "Warm",         # Chaleureuse — bonne pour Anna
    "Puck":     "Upbeat",
    "Charon":   "Informative",
    "Kore":     "Firm",
    "Fenrir":   "Excitable",
    "Aoede":    "Breezy",
    "Leda":     "Youthful",
    "Orus":     "Firm",
    "Perseus":  "Easygoing",
    "Achernar": "Soft",
    "Schedar":  "Even",
    "Gacrux":   "Mature",
    "Pulcherrima": "Forward",
    "Achird":   "Friendly",
    "Zubenelgenubi": "Casual",
    "Vindemiatrix": "Gentle",
    "Sadachbia": "Lively",
    "Sadaltager": "Knowledgeable",
    "Sulafat":  "Warm",
}

DEFAULT_VOICE = "Zephyr"


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Génère un header WAV pour les données audio brutes."""
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE",
        b"fmt ", 16, 1, num_channels,
        rate, byte_rate, block_align, bits_per_sample,
        b"data", data_size
    )
    return header + audio_data


def generate_tts(text: str, output_ogg: str, voice: str = DEFAULT_VOICE) -> bool:
    """
    Génère un message vocal via Gemini TTS et le sauvegarde en OGG Opus.

    Args:
        text: Texte à synthétiser
        output_ogg: Chemin du fichier OGG de sortie (pour WhatsApp)
        voice: Nom de la voix Gemini (défaut: Zephyr)

    Returns:
        True si succès, False sinon
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Chercher dans le fichier credentials OpenClaw
        creds_path = os.path.expanduser("~/.openclaw/credentials/gemini.json")
        if os.path.exists(creds_path):
            import json
            with open(creds_path) as f:
                api_key = json.load(f).get("api_key")

    if not api_key:
        print("❌ GEMINI_API_KEY non trouvée.")
        print("   export GEMINI_API_KEY='votre_clé'")
        print("   Ou créer ~/.openclaw/credentials/gemini.json avec {\"api_key\": \"...\"}")
        return False

    client = genai.Client(api_key=api_key)

    config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
    )

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)],
        )
    ]

    # Collecter tous les chunks audio
    audio_chunks = []
    mime_type_detected = None

    try:
        for chunk in client.models.generate_content_stream(
            model="gemini-2.5-flash-preview-tts",
            contents=contents,
            config=config,
        ):
            if chunk.parts is None:
                continue
            part = chunk.parts[0]
            if part.inline_data and part.inline_data.data:
                audio_chunks.append(part.inline_data.data)
                if mime_type_detected is None:
                    mime_type_detected = part.inline_data.mime_type
    except Exception as e:
        print(f"❌ Erreur Gemini API: {e}")
        return False

    if not audio_chunks:
        print("❌ Aucun audio reçu de Gemini")
        return False

    # Assembler et convertir en WAV si nécessaire
    raw_audio = b"".join(audio_chunks)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        tmp_wav_path = tmp_wav.name
        ext = mimetypes.guess_extension(mime_type_detected) if mime_type_detected else None
        if ext and ext != ".wav":
            tmp_wav.write(raw_audio)
        else:
            wav_data = convert_to_wav(raw_audio, mime_type_detected or "audio/L16;rate=24000")
            tmp_wav.write(wav_data)

    # Convertir WAV → OGG Opus (format requis WhatsApp)
    try:
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", tmp_wav_path,
            "-c:a", "libopus",
            "-b:a", "64k",
            "-ar", "48000",
            "-ac", "1",
            "-application", "voip",
            output_ogg
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Erreur ffmpeg: {result.stderr[-300:]}")
            return False

        size_kb = os.path.getsize(output_ogg) / 1024
        print(f"✅ Audio généré: {output_ogg} ({size_kb:.1f} KB) — voix: {voice}")
        return True

    except FileNotFoundError:
        print("❌ ffmpeg non trouvé. Installer: apt install ffmpeg")
        return False
    finally:
        os.unlink(tmp_wav_path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    text_input = sys.argv[1]
    output_path = sys.argv[2]

    # Options
    voice_name = DEFAULT_VOICE
    for i, arg in enumerate(sys.argv):
        if arg == "--voice" and i + 1 < len(sys.argv):
            voice_name = sys.argv[i + 1]

    if voice_name not in VOICES:
        print(f"⚠️  Voix '{voice_name}' inconnue. Voix disponibles:")
        for v, desc in VOICES.items():
            print(f"   {v}: {desc}")
        sys.exit(1)

    success = generate_tts(text_input, output_path, voice_name)
    sys.exit(0 if success else 1)