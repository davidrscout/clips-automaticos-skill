# -*- coding: utf-8 -*-
"""Utilidades comunes: config, rutas, log, ffmpeg, cerebro (IA), candados.

Multi-cuenta: cada proceso trabaja para UNA cuenta, elegida con la variable de entorno CLIPS_CUENTA.
Las rutas son cuentas/<cuenta>/{fuentes,trabajo,listos,subidos} y cfg() devuelve la config global con la sección
de la cuenta encima (y su bloque `estilo` mezclado con el estilo global). clips.py lanza un subproceso por cuenta."""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent
CUENTA = os.environ.get("CLIPS_CUENTA", "")
BASE = RAIZ / "cuentas" / (CUENTA or "_sin_cuenta")
FUENTES, TRABAJO, LISTOS, SUBIDOS = (BASE / d for d in ("fuentes", "trabajo", "listos", "subidos"))
LOGS = RAIZ / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
if CUENTA:
    for d in (FUENTES, TRABAJO, LISTOS, SUBIDOS):
        d.mkdir(parents=True, exist_ok=True)
ESTADO = BASE / "estado.json"
WINDOWS = os.name == "nt"
# Con pythonw (tareas programadas de Windows) los subprocesos no deben abrir consola
SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def cargar_env():
    """Lee RAIZ/.env (CLAVE=valor) sin pisar variables ya definidas. Ahí van las claves de API y tokens."""
    f = RAIZ / ".env"
    if not f.exists():
        return
    for linea in f.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


cargar_env()


def cfg_global():
    with open(RAIZ / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def cuentas_activas():
    return [m for m, v in (cfg_global().get("cuentas") or {}).items() if (v or {}).get("activo", True)]


def mezclar(base, encima):
    """Mezcla profunda de diccionarios: lo de `encima` gana."""
    out = dict(base or {})
    for k, v in (encima or {}).items():
        out[k] = mezclar(out.get(k), v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def cfg(cuenta=None):
    g = cfg_global()
    cuenta = cuenta or CUENTA
    m = (g.get("cuentas") or {}).get(cuenta) or {}
    c = mezclar({k: v for k, v in g.items() if k != "cuentas"}, m)
    c["cuenta"] = cuenta
    return c


def estilo(c=None):
    """Bloque `estilo` ya mezclado (global + cuenta) con valores por defecto."""
    c = c or cfg()
    por_defecto = {
        "editor": "",
        "corte": "momentos", "clip_min_seg": 25, "clip_max_seg": 60, "clips_por_video_max": 8,
        "encuadre": "auto", "velocidad": 1.0, "calidad_crf": 20,
        "subtitulos": {"activo": True, "fuente": "Montserrat ExtraBold", "tamano": 78, "color": "#FFFFFF",
                       "color_activo": "#FFE500", "contorno": 6, "color_contorno": "#000000", "sombra": 2,
                       "mayusculas": True, "palabras_por_linea": 3, "salto": 110, "altura": None},
        "gancho": {"activo": True, "tamano": 80, "color_texto": "#FFFFFF", "color_fondo": "#000000",
                   "segundos": 0, "altura": None, "mayusculas": True},
        "logo": {"fichero": "", "posicion": "arriba-derecha", "ancho": 180, "opacidad": 0.85, "margen": 40},
        "musica": {"carpeta": "", "volumen": 0.12},
        "textos": {"idioma": None, "hashtags_base": [], "max_hashtags": 6, "credito": True,
                   "plantilla_credito": "Source: {canal} — {url}"},
    }
    return mezclar(por_defecto, c.get("estilo") or {})


def ahora(c=None):
    """Hora actual en la zona horaria de la cuenta (las franjas de subida se piensan en la hora de su público)."""
    c = c or cfg()
    zona = c.get("zona_horaria")
    if zona:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo(zona)).replace(tzinfo=None)
    return datetime.datetime.now()


def log(msg, fichero="clips.log"):
    linea = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} [{CUENTA or '-'}] {msg}"
    try:
        print(linea, flush=True)
    except (UnicodeEncodeError, OSError):  # consola cp1252 con emojis, o sin consola (pythonw)
        pass
    with open(LOGS / fichero, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def estado():
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except Exception:
        return {"fuentes_hechas": [], "subidas": []}


def guardar_estado(s):
    ESTADO.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def ffmpeg(nombre="ffmpeg"):
    exe = shutil.which(nombre)
    if not exe:
        for p in (Path(os.environ.get("LOCALAPPDATA", "")) / f"Microsoft/WinGet/Links/{nombre}.exe",
                  Path(f"C:/ffmpeg/bin/{nombre}.exe"), Path(f"/opt/homebrew/bin/{nombre}"), Path(f"/usr/local/bin/{nombre}")):
            if p.exists():
                return str(p)
        sys.exit(f"{nombre} no encontrado. Ejecuta: python instalar.py")
    return exe


def run(args, **kw):
    """Ejecuta un comando y devuelve (rc, stdout, stderr) en texto."""
    kw.setdefault("creationflags", SIN_VENTANA)
    r = subprocess.run(args, capture_output=True, **kw)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


# ------------------------------------------------------------------ cerebro (IA para elegir momentos y títulos)
def preguntar_ia(prompt, timeout=300, c=None):
    """Devuelve el texto de la IA configurada en `cerebro`:
      tipo: api      -> cualquier API compatible con OpenAI (Gemini, OpenRouter, OpenAI, Groq, LM Studio, Ollama...)
      tipo: comando  -> un CLI que lee el prompt por stdin (claude -p, gemini, llm...)
      tipo: ninguno  -> sin IA (solo corte secuencial con títulos sacados del texto)"""
    c = c or cfg()
    ce = c.get("cerebro") or {}
    tipo = ce.get("tipo", "api")
    if tipo == "api":
        import requests
        clave = os.environ.get(ce.get("clave_env") or "", "")
        cab = {"Authorization": f"Bearer {clave}"} if clave else {}
        r = requests.post(ce["url"], headers=cab, timeout=timeout, json={
            "model": ce.get("modelo"), "temperature": ce.get("temperatura", 0.5),
            "messages": [{"role": "user", "content": prompt}]})
        if r.status_code >= 400:
            raise RuntimeError(f"API {r.status_code}: {r.text[:200]}")
        return r.json()["choices"][0]["message"]["content"]
    if tipo == "comando":
        cmd = list(ce.get("comando") or ["claude", "-p", "--output-format", "text"])
        cmd[0] = shutil.which(cmd[0]) or cmd[0]
        r = subprocess.run(cmd, input=prompt.encode("utf-8"), capture_output=True, timeout=timeout,
                           creationflags=SIN_VENTANA)
        return r.stdout.decode("utf-8", "replace")
    return ""


def pedir_json(prompt, timeout=300, c=None):
    """Pregunta a la IA y extrae el primer objeto JSON de la respuesta (None si falla)."""
    try:
        salida = preguntar_ia(prompt, timeout, c)
        m = re.search(r"\{.*\}", salida or "", re.S)
        return json.loads(m.group(0)) if m else None
    except Exception as e:
        log(f"  cerebro falló: {type(e).__name__}: {str(e)[:160]}")
        return None


def slug(texto, n=60):
    t = re.sub(r"[^\w\s-]", "", str(texto), flags=re.U).strip().lower()
    t = re.sub(r"[\s_-]+", "-", t)
    return t[:n] or "clip"


def chrome_exe(c=None):
    c = c or cfg()
    if c.get("chrome_exe"):
        return c["chrome_exe"]
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe"),
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable"):
        if Path(p).exists():
            return p
    return None


def en_cuentas(script, args=(), cuentas=None):
    """Ejecuta `script` una vez por cuenta activa (subproceso con CLIPS_CUENTA)."""
    for m in cuentas or cuentas_activas():
        env = {**os.environ, "CLIPS_CUENTA": m, "PYTHONIOENCODING": "utf-8"}
        subprocess.run([sys.executable, str(RAIZ / script), *args], env=env, cwd=str(RAIZ), creationflags=SIN_VENTANA)


def candado(nombre):
    """Candado de proceso: devuelve el fichero abierto si lo consigue, None si otro proceso lo tiene.
    Mantener la referencia viva mientras dure el trabajo; se suelta solo al terminar el proceso."""
    f = open(LOGS / f"{nombre}.lock", "a+")
    try:
        if WINDOWS:
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except OSError:
        f.close()
        return None


def avisar_telegram(texto):
    """Aviso opcional por Telegram (token en .env, chat_id en config). Falla en silencio."""
    try:
        c = cfg()
        t = c.get("telegram") or {}
        chat = str(t.get("chat_id") or "").strip()
        token = os.environ.get(t.get("token_env") or "TELEGRAM_BOT_TOKEN", "")
        if not (token and chat):
            return
        import requests
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": f"[{CUENTA}] {texto}"[:4000]}, timeout=10)
    except Exception:
        pass
