# -*- coding: utf-8 -*-
"""Saca clips de cada transcripción y escribe trabajo/<nombre>.clips.json.
  estilo.corte: momentos   -> la IA lee la transcripción entera y elige los mejores momentos (gancho en 3 s)
  estilo.corte: secuencial -> trocea en clips de min-max s cortando en fin de frase (Parte 1, 2, 3...)
La forma de elegir y titular se personaliza por cuenta con estilo.editor (instrucciones libres para la IA).
Uso: python cortar.py"""
import json
import re

from comun import FUENTES, TRABAJO, cfg, estilo, log, pedir_json

FIN_FRASE = re.compile(r"[.!?…]$|[.!?]['\")]$")
LENGUAS = {"es": "español de España", "en": "English", "pt": "português", "fr": "français", "it": "italiano",
           "de": "Deutsch"}


def trocear(palabras, mn, mx):
    """Agrupa palabras en clips: cierra el clip en el primer final de frase pasado `mn` s, o a la fuerza en `mx`."""
    clips, actual = [], []
    for p in palabras:
        if not actual:
            actual = [p]
            continue
        if p["fin"] - actual[0]["ini"] > mx:  # esta palabra ya no cabe: se cierra el clip antes de ella
            clips.append(actual)
            actual = [p]
            continue
        dur = p["fin"] - actual[0]["ini"]
        actual.append(p)
        if dur >= mn and FIN_FRASE.search(p["w"]):
            clips.append(actual)
            actual = []
    if actual and (actual[-1]["fin"] - actual[0]["ini"]) >= mn * 0.6:
        clips.append(actual)
    return clips


def texto_de(palabras):
    return " ".join(p["w"] for p in palabras).strip()


def lengua_de(c, e):
    cod = (e["textos"].get("idioma") or c.get("idioma") or "en").split("-")[0]
    return LENGUAS.get(cod, cod)


def bloque_editor(e):
    extra = (e.get("editor") or "").strip()
    return f"\n\nINSTRUCCIONES DE ESTA CUENTA (mandan sobre lo anterior):\n{extra}\n" if extra else ""


def pedir_meta(c, e, texto, fuente):
    prompt = (f"Eres editor de clips para TikTok y YouTube Shorts. Este es el texto de un clip sacado del vídeo "
              f"«{fuente}»:\n\n«{texto}»\n\nEscribe TODO en {lengua_de(c, e)}, natural y nativo."
              f"{bloque_editor(e)}\n"
              "Devuelve SOLO un JSON con: titulo (máx 60 caracteres, con gancho, sin comillas), gancho (texto en "
              "pantalla, máx 6 palabras), descripcion (1-2 frases), hashtags (lista de 3-5, con #).")
    d = pedir_json(prompt, 180, c)
    return d if d and d.get("titulo") else None


# ------------------------------------------------------------------ momentos virales
def frases(palabras):
    out, actual = [], []
    for p in palabras:
        actual.append(p)
        if FIN_FRASE.search(p["w"]) or len(actual) >= 40:
            out.append(actual); actual = []
    if actual:
        out.append(actual)
    return out


def info_video(nombre):
    """Título y canal del vídeo fuente (yt-dlp deja <id>.info.json en fuentes/)."""
    try:
        d = json.loads((FUENTES / f"{nombre}.info.json").read_text(encoding="utf-8"))
        return d.get("title", nombre), d.get("channel") or d.get("uploader") or ""
    except Exception:
        return nombre, ""


PROMPT_MOMENTOS = """Eres el mejor editor de clips virales de TikTok y YouTube Shorts. Transcripción con tiempos (segundos)
del vídeo «{titulo}» de {canal}:

{lineas}

Elige hasta {n} MOMENTOS que funcionarían solos como clip viral, de {mn} a {mx} segundos cada uno.
- Cada clip EMPIEZA con una frase que engancha en los primeros 3 segundos: polémica, sorpresa, pregunta, momento
  gracioso, reacción fuerte, cifra brutal, reto, apuesta.
- TERMINA con remate o cierre natural, sin cortar a mitad de idea. Se entiende sin ver el vídeo entero.
- Nada de intros, patrocinios ni despedidas. No se solapan. Ordenados del más viral al menos.
- Textos en {lengua} nativo.{editor}
Devuelve SOLO un JSON: {{"clips": [{{"ini": segundo_inicio, "fin": segundo_fin, "gancho": "texto en pantalla, máx 6 palabras",
"titulo": "máx 70 caracteres, con gancho", "descripcion": "1 frase", "hashtags": ["#..", "#.."], "viral": 1-10}}]}}
Usa tiempos que coincidan con inicios y finales de frase de la transcripción."""


def momentos(c, e, d, nombre, mn, mx, n_max):
    titulo, canal = info_video(nombre)
    lineas = "\n".join(f"[{f[0]['ini']:.1f}-{f[-1]['fin']:.1f}] {texto_de(f)}" for f in frases(d["palabras"]))
    prompt = PROMPT_MOMENTOS.format(titulo=titulo, canal=canal or "?", lineas=lineas, n=n_max, mn=mn, mx=mx,
                                    lengua=lengua_de(c, e), editor=bloque_editor(e))
    res = pedir_json(prompt, 900, c) or {}
    out = []
    for m in res.get("clips", []):
        try:
            ini, fin = float(m["ini"]), float(m["fin"])
        except Exception:
            continue
        pal = [p for p in d["palabras"] if p["ini"] >= ini - 0.4 and p["fin"] <= fin + 0.4]
        if not pal:
            continue
        dur = pal[-1]["fin"] - pal[0]["ini"]
        if dur < mn * 0.7 or dur > mx * 1.15:
            log(f"  momento descartado por duración ({dur:.0f}s): {m.get('titulo')}")
            continue
        out.append((m, pal))
    return out[:n_max]


def etiquetas(lista, e):
    base = e["textos"].get("hashtags_base") or []
    tags = [t if t.startswith("#") else "#" + t for t in (lista or [])] + base
    return list(dict.fromkeys(tags))[: int(e["textos"].get("max_hashtags", 6))]


def main():
    c = cfg()
    e = estilo(c)
    mn, mx = int(e["clip_min_seg"]), int(e["clip_max_seg"])
    n_max = int(e["clips_por_video_max"])
    sin_ia = (c.get("cerebro") or {}).get("tipo") == "ninguno"
    for tj in sorted(TRABAJO.glob("*.palabras.json")):
        nombre = tj.name.replace(".palabras.json", "")
        salida = TRABAJO / f"{nombre}.clips.json"
        if salida.exists():
            continue
        d = json.loads(tj.read_text(encoding="utf-8"))
        if d.get("descartado") or not d.get("palabras"):
            continue
        clips = []
        if e["corte"] == "momentos" and not sin_ia:
            elegidos = momentos(c, e, d, nombre, mn, mx, n_max)
            if not elegidos:
                log(f"{nombre}: la IA no devolvió momentos válidos; se reintentará en la próxima pasada")
                continue
            log(f"{nombre}: {len(elegidos)} momentos")
            for i, (m, pal) in enumerate(elegidos, 1):
                clips.append({"n": i, "ini": pal[0]["ini"], "fin": pal[-1]["fin"], "titulo": str(m.get("titulo", ""))[:95],
                              "gancho": str(m.get("gancho", ""))[:60], "descripcion": m.get("descripcion", ""),
                              "hashtags": etiquetas(m.get("hashtags"), e), "viral": m.get("viral"),
                              "palabras": pal, "suelto": True})
                log(f"  momento {i}: {pal[0]['ini']:.0f}-{pal[-1]['fin']:.0f}s · {m.get('viral')}/10 · {m.get('titulo')}")
        else:
            trozos = trocear(d["palabras"], mn, mx)[:n_max]
            log(f"{nombre}: {len(trozos)} clips")
            for i, pal in enumerate(trozos, 1):
                texto = texto_de(pal)
                meta = (None if sin_ia else pedir_meta(c, e, texto, info_video(nombre)[0])) or {}
                titulo = (meta.get("titulo") or texto[:57] + "...").strip()[:95]
                clips.append({"n": i, "ini": pal[0]["ini"], "fin": pal[-1]["fin"], "titulo": titulo,
                              "gancho": str(meta.get("gancho", ""))[:60],
                              "descripcion": (meta.get("descripcion") or texto[:140]).strip(),
                              "hashtags": etiquetas(meta.get("hashtags"), e), "palabras": pal})
                log(f"  clip {i}: {pal[0]['ini']:.0f}-{pal[-1]['fin']:.0f}s · {titulo}")
        salida.write_text(json.dumps({"video": d["video"], "clips": clips}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
