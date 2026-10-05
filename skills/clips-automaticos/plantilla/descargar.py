# -*- coding: utf-8 -*-
"""Descarga las fuentes a cuentas/<cuenta>/fuentes/: las URLs fijas de config (fuentes.urls), los vídeos que dejó
buscar.py y los ficheros de fuentes.carpeta_local. Cada fuente se procesa una sola vez (estado.json).
Uso: python descargar.py"""
import shutil
from pathlib import Path

from buscar import ytdlp
from comun import FUENTES, cfg, estado, guardar_estado, log, slug

VIDEO = (".mp4", ".mkv", ".webm", ".mov")


def descargar_url(url):
    salida = str(FUENTES / "%(id)s.%(ext)s")
    rc, out, err = ytdlp(["--no-playlist" if "list=" not in url else "--yes-playlist",
                          "-f", "bv*[height<=1080]+ba/b[height<=1080]", "--merge-output-format", "mp4",
                          "--write-info-json", "--no-overwrites", "-o", salida, url])
    if rc != 0:
        log(f"ERROR descargando {url}: {err[-400:]}")
        return False
    return True


def main():
    c = cfg()
    f = c.get("fuentes") or {}
    st = estado()
    hechas = set(st.get("fuentes_hechas", []))
    locales = []
    if f.get("carpeta_local"):
        carpeta = Path(f["carpeta_local"]).expanduser()
        locales = [str(p) for p in sorted(carpeta.glob("*")) if p.suffix.lower() in VIDEO] if carpeta.exists() else []
    for fuente in list(f.get("urls") or []) + list(st.get("auto_cola", [])) + locales:
        fuente = str(fuente).strip()
        if not fuente or fuente in hechas:
            continue
        log(f"Fuente: {fuente}")
        if fuente.lower().startswith("http"):
            if not descargar_url(fuente):
                continue
        else:
            p = Path(fuente)
            dest = FUENTES / (slug(p.stem) + p.suffix.lower())
            if not dest.exists():
                shutil.copy2(p, dest)
                log(f"Copiado {p} -> {dest.name}")
        hechas.add(fuente)
        st["fuentes_hechas"] = sorted(hechas)
        st["auto_cola"] = [u for u in st.get("auto_cola", []) if u not in hechas]
        guardar_estado(st)


if __name__ == "__main__":
    main()
