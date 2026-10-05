# -*- coding: utf-8 -*-
"""Busca vídeos fuente nuevos SOLO cuando hacen falta (si la reserva de clips listos se está acabando):
  - canales: los vídeos recientes más vistos de cada canal de YouTube de la lista
  - busquedas_cc: búsquedas de YouTube filtradas a licencia Creative Commons BY (reutilizables citando al autor)
Los mete en estado.json -> "auto_cola", que descargar.py procesa. Uso: python buscar.py [--forzar]"""
import json
import sys
import urllib.parse
from pathlib import Path

from comun import LISTOS, cfg, estado, guardar_estado, log, run

FILTRO_CC = "EgIwAQ%3D%3D"  # filtro de YouTube "Creative Commons"


def ytdlp(args):
    # YouTube exige un motor JS para algunos formatos: `pip install deno` lo deja junto al python del venv
    carpeta = Path(sys.executable).parent
    deno = next((p for p in (carpeta / "deno.exe", carpeta / "deno") if p.exists()), None)
    js = ["--js-runtimes", f"deno:{deno}"] if deno else []
    return run([sys.executable, "-m", "yt_dlp", *js, "--no-warnings", *args])


def clips_en_cola(c):
    """Cuántos clips quedan por subir en la red más atrasada."""
    redes = [r for r, v in (c.get("redes") or {}).items() if v.get("activo")]
    pend = {r: 0 for r in redes}
    for j in LISTOS.glob("*.json"):
        try:
            m = json.loads(j.read_text(encoding="utf-8"))
        except Exception:
            continue
        for r in redes:
            if r not in (m.get("subido") or {}):
                pend[r] += 1
    return min(pend.values()) if pend else 0


def _lista(url, n, a, vistas_min):
    rc, out, err = ytdlp(["--flat-playlist", "--playlist-end", str(n), "--print",
                          "%(id)s\t%(duration)s\t%(view_count)s", url])
    res = []
    for linea in out.splitlines():
        try:
            vid, dur, vistas = linea.split("\t")
            dur = float(dur); vistas = int(vistas) if vistas not in ("NA", "None") else 0
        except ValueError:
            continue
        if a["duracion_min"] * 60 <= dur <= a["duracion_max"] * 60 and vistas >= vistas_min:
            res.append((vistas, vid))
    return [v for _, v in sorted(res, reverse=True)]  # los más vistos primero


def candidatos_cc(q, a):
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}&sp={FILTRO_CC}"
    return _lista(url, 40, a, a["vistas_min"])


def candidatos_canal(canal, a):
    url = canal if canal.startswith("http") else f"https://www.youtube.com/{canal.lstrip('/')}/videos"
    return _lista(url, a.get("ultimos", 8), a, a["vistas_min_canal"])


def ficha(vid):
    rc, out, err = ytdlp(["--skip-download", "--dump-json", f"https://www.youtube.com/watch?v={vid}"])
    try:
        return json.loads(out)
    except Exception:
        return None


def main():
    c = cfg()
    a = {"canales": [], "busquedas_cc": [], "duracion_min": 4, "duracion_max": 180, "vistas_min": 20000,
         "vistas_min_canal": 100000, "ultimos": 8, "reserva_dias": 2, "nuevas_max": 3, **(c.get("fuentes") or {})}
    fuentes = [("canal", x) for x in a["canales"] or []] + [("cc", x) for x in a["busquedas_cc"] or []]
    if not fuentes:
        return
    st = estado()
    cola = st.setdefault("auto_cola", [])
    vistos = set(st.setdefault("auto_vistos", []))
    por_dia = max((v.get("por_dia", 1) for v in (c.get("redes") or {}).values() if v.get("activo")), default=1)
    hay = clips_en_cola(c)
    if "--forzar" not in sys.argv and (hay >= por_dia * a["reserva_dias"] or cola):
        log(f"Fuentes: hay reserva ({hay} clips en cola, {len(cola)} vídeos por procesar), no busco")
        return
    idioma = (c.get("idioma") or "auto").split("-")[0]
    nuevas, usadas = 0, 0
    ini = st.get("auto_rotacion", 0) % len(fuentes)  # rotar para no tirar siempre de la misma fuente
    for tipo, q in fuentes[ini:] + fuentes[:ini]:
        usadas += 1
        lista = candidatos_canal(q, a) if tipo == "canal" else candidatos_cc(q, a)
        for vid in lista:
            if vid in vistos:
                continue
            vistos.add(vid)
            f = ficha(vid)
            if not f:
                continue
            lic = f.get("license") or ""
            leng = (f.get("language") or "").split("-")[0]
            if tipo == "cc" and "Creative Commons" not in lic:
                continue
            if leng and idioma != "auto" and leng != idioma:
                continue
            url = f"https://www.youtube.com/watch?v={vid}"
            cola.append(url)
            st.setdefault("origen", {})[vid] = {"canal": f.get("channel") or f.get("uploader"), "url": url,
                                                "titulo": f.get("title"), "licencia": lic, "tipo": tipo}
            log(f"Fuente nueva ({q}): {f.get('title')} · {f.get('channel')} · {f.get('view_count')} visitas")
            nuevas += 1
            break  # un vídeo por fuente y pasada: variedad de creadores
        if nuevas >= a["nuevas_max"]:
            break
    st["auto_rotacion"] = ini + usadas
    st["auto_vistos"] = sorted(vistos)
    guardar_estado(st)
    if not nuevas:
        log("Fuentes: no encontré vídeos nuevos que cumplan los filtros")


if __name__ == "__main__":
    main()
