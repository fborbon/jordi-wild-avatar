"""Quick mic test: records 4 seconds, shows live level, then plays back."""
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wavfile
import tempfile, os

RATE = 16000
DURATION = 4

print("Dispositivos de audio disponibles:")
print(sd.query_devices())
print(f"\nDispositivo de entrada por defecto: {sd.query_devices(kind='input')['name']}")
print("\nGrabando 4 segundos... HABLA AHORA")

frames = []
GAIN = 0.1   # match MIC_GAIN in avatar

def callback(indata, f, t, status):
    frames.append((indata * GAIN).copy())
    raw       = np.abs(indata).mean()
    postgain  = raw * GAIN
    level     = int(postgain * 400)
    bar       = "#" * min(level, 30) + "-" * max(0, 30 - level)
    status    = "OK" if 0.02 < postgain < 0.4 else ("sin señal" if postgain <= 0.02 else "muy alto")
    print(f"\r  [{bar}] raw={raw:.3f}  post-gain={postgain:.3f}  {status}", end="", flush=True)

with sd.InputStream(samplerate=RATE, channels=1, dtype=np.float32, callback=callback, blocksize=1024):
    sd.sleep(DURATION * 1000)

print("\n\nReproduciendo lo grabado...")
audio = np.concatenate(frames)
peak = np.abs(audio).max()
print(f"  Nivel máximo capturado: {peak:.4f}  ({'OK' if peak > 0.01 else 'MUY BAJO — revisa micrófono'})")
sd.play(audio, samplerate=RATE)
sd.wait()
print("Listo.")
