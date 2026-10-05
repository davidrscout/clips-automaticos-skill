# -*- coding: utf-8 -*-
"""Instalación en un paso (Windows, Mac o Linux). Ejecutar con el python del sistema (3.10+):
    python instalar.py
Crea venv/, instala dependencias, comprueba ffmpeg y Chrome, y deja config.yaml y .env listos para rellenar."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
WIN = os.name == "nt"


def paso(t):
    print(f"\n=== {t} ===", flush=True)


def main():
    if sys.version_info < (3, 10):
        sys.exit("Hace falta Python 3.10 o superior.")
    paso("ffmpeg")
    if not shutil.which("ffmpeg"):
        if WIN:
            subprocess.call(["winget", "install", "-e", "--id", "Gyan.FFmpeg", "--accept-source-agreements",
                             "--accept-package-agreements"])
            print("Si acaba de instalarse, CIERRA y vuelve a abrir la terminal para que se vea ffmpeg.")
        elif sys.platform == "darwin" and shutil.which("brew"):
            subprocess.call(["brew", "install", "ffmpeg"])
        else:
            print("Instala ffmpeg con tu gestor de paquetes (ej.: sudo apt install ffmpeg) y vuelve a ejecutar.")
    else:
        print("ffmpeg OK")

    paso("entorno virtual + dependencias")
    venv = RAIZ / "venv"
    if not venv.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
    py = venv / ("Scripts/python.exe" if WIN else "bin/python")
    subprocess.check_call([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([str(py), "-m", "pip", "install", "-r", str(RAIZ / "requirements.txt")])
    if WIN:  # GPU NVIDIA: librerías CUDA para faster-whisper. Si falla, se usa CPU automáticamente.
        subprocess.call([str(py), "-m", "pip", "install", "nvidia-cublas-cu12", "nvidia-cudnn-cu12"])

    paso("Chrome")
    candidatos = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                  str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe"),
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable"]
    exe = next((p for p in candidatos if Path(p).exists()), None) or shutil.which("google-chrome")
    print(f"Chrome: {exe}" if exe else "NO encuentro Google Chrome: instálalo o pon su ruta en config.yaml -> chrome_exe")

    paso("ficheros de configuración")
    for ejemplo, real in (("config.ejemplo.yaml", "config.yaml"), (".env.ejemplo", ".env")):
        if not (RAIZ / real).exists():
            shutil.copy(RAIZ / ejemplo, RAIZ / real)
            print(f"Creado {real} (a partir de {ejemplo})")
        else:
            print(f"{real} ya existe, no lo toco")

    cmd = r"venv\Scripts\python clips.py" if WIN else "venv/bin/python clips.py"
    print(f"""
Listo. Siguientes pasos:
  1. Rellena config.yaml (cuentas, redes, estilo) y .env (clave de la IA).
  2. {cmd} login          -> inicia sesión en TikTok/YouTube en cada perfil y cierra las ventanas
  3. {cmd} procesar --cuenta <cuenta>
  4. {cmd} previa --cuenta <cuenta>   -> revisa previas/ y ajusta el estilo
  5. {cmd} subir --cuenta <cuenta> --red tiktok --ahora 1   -> prueba de subida
  6. {cmd} programar      -> automático para siempre""")


if __name__ == "__main__":
    main()
