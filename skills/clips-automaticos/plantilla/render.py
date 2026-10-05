# -*- coding: utf-8 -*-
"""Renderiza cada clip a vertical 1080x1920 según el `estilo` de la cuenta:
  - encuadre: auto (sigue la cara / apila 2 personas / difuminado, ver reencuadre.py) | seguir | blur | crop
  - subtítulos quemados palabra a palabra (palabra activa en otro color con «salto»), fuente/colores/tamaño/altura
  - gancho (texto fijo arriba), logo/marca de agua, música de fondo, velocidad
Entrada: trabajo/<nombre>.clips.json + fuentes/<video>. Salida: listos/<nombre>_NN.mp4 + .json (título, descripción...).
Uso: python render.py            renderiza lo que falte
     python render.py --rehacer  vuelve a renderizar con el estilo actual los clips listos que aún no se han subido a ninguna red
     python render.py --previa   renderiza solo 1 clip en previas/<cuenta>.mp4 (+ fotogramas .jpg) para revisar el estilo"""
import json
import random
import re
import sys
from pathlib import Path

from comun import CUENTA, FUENTES, LISTOS, RAIZ, TRABAJO, cfg, estado, estilo, ffmpeg, log, run

AUDIO_EXT = (".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac")


def color_ass(hexa, alfa="00"):
    """'#RRGGBB' -> '&HAABBGGRR' (ASS va en BGR)."""
    h = str(hexa).lstrip("#")
    if len(h) != 6:
        h = "FFFFFF"
    return f"&H{alfa}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def ass_tiempo(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def limpio(w, mayus=True):
    w = w.replace("{", "").replace("}", "").replace("\\", "")
    return w.upper() if mayus else w


def ass_de(palabras, ini, e, gancho="", dur=0, modo="blur"):
    s, g = e["subtitulos"], e["gancho"]
    # dónde va cada cosa según el encuadre: en "dividir" los subtítulos van en la junta de las dos personas
    margen_sub = s.get("altura") or {"dividir": 890, "seguir": 380}.get(modo, 420)
    margen_gancho = g.get("altura") or (70 if modo == "dividir" else 240)
    cab = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n[V4+ Styles]\n"
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
           "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           f"Style: Sub,{s['fuente']},{int(s['tamano'])},{color_ass(s['color'])},{color_ass(s['color'])},"
           f"{color_ass(s['color_contorno'])},&H80000000,1,0,0,0,100,100,0,0,1,{s['contorno']},{s['sombra']},2,60,60,{int(margen_sub)},1\n"
           f"Style: Gancho,{s['fuente']},{int(g['tamano'])},{color_ass(g['color_texto'])},{color_ass(g['color_texto'])},"
           f"{color_ass(g['color_fondo'])},{color_ass(g['color_fondo'])},1,0,0,0,100,100,0,0,3,16,0,8,70,70,{int(margen_gancho)},1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    ev = []
    if s.get("activo", True):
        n = max(1, int(s.get("palabras_por_linea", 3)))
        mayus = s.get("mayusculas", True)
        activo = color_ass(s["color_activo"])[4:]  # BBGGRR para la etiqueta \c
        salto = int(s.get("salto", 110))
        grupos, gr, subs = [], [], []
        for p in palabras:
            gr.append(p)
            if len(gr) == n or re.search(r"[.!?,;:…]$", p["w"]):
                grupos.append(gr); gr = []
        if gr:
            grupos.append(gr)
        for k, gr in enumerate(grupos):
            fin_grupo = gr[-1]["fin"] - ini + 0.15
            if k + 1 < len(grupos):  # nunca dos líneas a la vez: el grupo acaba como tarde cuando empieza el siguiente
                fin_grupo = min(fin_grupo, grupos[k + 1][0]["ini"] - ini)
            for i, p in enumerate(gr):  # un evento por palabra: la que suena, en color y con «salto»
                a = max(0, p["ini"] - ini)
                b = (gr[i + 1]["ini"] - ini) if i + 1 < len(gr) else fin_grupo
                texto = " ".join(
                    (f"{{\\c&H{activo}&\\fscx{salto}\\fscy{salto}}}{limpio(x['w'], mayus)}{{\\r}}"
                     if j == i else limpio(x["w"], mayus)) for j, x in enumerate(gr))
                subs.append([a, max(b, a + 0.05), texto])
        for k in range(1, len(subs)):  # encadenar: cada palabra empieza cuando acaba la anterior, nunca antes
            subs[k][0] = max(subs[k][0], subs[k - 1][1])
            subs[k][1] = max(subs[k][1], subs[k][0] + 0.02)
        ev += [f"Dialogue: 0,{ass_tiempo(x)},{ass_tiempo(y)},Sub,,0,0,0,,{t}" for x, y, t in subs]
    if g.get("activo", True) and gancho and dur:
        fin = min(dur, float(g["segundos"])) if float(g.get("segundos") or 0) > 0 else dur
        ev.insert(0, f"Dialogue: 1,{ass_tiempo(0)},{ass_tiempo(fin)},Gancho,,0,0,0,,{limpio(gancho, g.get('mayusculas', True))}")
    return cab + "\n".join(ev) + "\n"


def filtro_base(encuadre, video, ini, dur, cmds):
    if encuadre in ("auto", "seguir"):
        import reencuadre
        return reencuadre.filtro(video, ini, dur, cmds, forzado=encuadre if encuadre == "seguir" else None)
    if encuadre == "crop":
        return "[0:v]scale=-2:1920,crop=1080:1920[v]", "crop"
    return ("[0:v]split=2[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:10[bg];"
            "[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"), "blur"


def ruta_ff(p):
    return str(p).replace("\\", "/").replace(":", "\\:")


POS_LOGO = {"arriba-derecha": ("W-w-{m}", "{m}"), "arriba-izquierda": ("{m}", "{m}"),
            "abajo-derecha": ("W-w-{m}", "H-h-{m}"), "abajo-izquierda": ("{m}", "H-h-{m}"),
            "abajo-centro": ("(W-w)/2", "H-h-{m}"), "arriba-centro": ("(W-w)/2", "{m}")}


def tiene_audio(video):
    rc, out, err = run([ffmpeg("ffprobe"), "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", str(video)])
    return bool(out.strip())


def elegir_musica(e):
    carpeta = (e.get("musica") or {}).get("carpeta")
    if not carpeta:
        return None
    p = Path(carpeta).expanduser()
    p = p if p.is_absolute() else RAIZ / p
    pistas = [x for x in p.glob("*") if x.suffix.lower() in AUDIO_EXT] if p.exists() else []
    return random.choice(pistas) if pistas else None


def render_clip(c, e, video, cl, out, nombre):
    """Renderiza un clip. Devuelve el encuadre usado o None si ffmpeg falló."""
    margen = 0.25
    ini = max(0, cl["ini"] - margen); dur = cl["fin"] - ini + margen
    v, modo = filtro_base(e.get("encuadre", "auto"), video, ini, dur, TRABAJO / f"{nombre}.cmds")
    v = v[: v.rindex("[v]")] + "[v0]"
    ultima = "v0"
    entradas = ["-ss", f"{ini:.2f}", "-t", f"{dur:.2f}", "-i", str(video)]
    # subtítulos + gancho (libass); fontsdir = fuentes_tipo/ para usar fuentes propias sin instalarlas
    ass = TRABAJO / f"{nombre}.ass"
    ass.write_text(ass_de(cl["palabras"], ini, e, cl.get("gancho", ""), dur, modo), encoding="utf-8")
    v += f";[{ultima}]subtitles='{ruta_ff(ass)}':fontsdir='{ruta_ff(RAIZ / 'fuentes_tipo')}'[v1]"; ultima = "v1"
    # música de fondo (entrada 1, en bucle)
    musica = elegir_musica(e)
    if musica:
        entradas += ["-stream_loop", "-1", "-i", str(musica)]
    # logo / marca de agua
    lg = e.get("logo") or {}
    logo = Path(lg["fichero"]).expanduser() if lg.get("fichero") else None
    if logo and not logo.is_absolute():
        logo = RAIZ / logo
    if logo and logo.exists():
        idx = 1 + bool(musica)
        entradas += ["-i", str(logo)]
        m = int(lg.get("margen", 40))
        x, y = (t.format(m=m) for t in POS_LOGO.get(lg.get("posicion", "arriba-derecha"), POS_LOGO["arriba-derecha"]))
        v += (f";[{idx}:v]scale={int(lg.get('ancho', 180))}:-1,format=rgba,"
              f"colorchannelmixer=aa={float(lg.get('opacidad', 0.85))}[lg];[{ultima}][lg]overlay={x}:{y}[v2]")
        ultima = "v2"
    elif logo:
        log(f"  logo no encontrado: {logo}")
    vel = float(e.get("velocidad") or 1.0)
    v += f";[{ultima}]setpts=PTS/{vel}[v]" if vel != 1.0 else f";[{ultima}]null[v]"
    # audio
    audio = tiene_audio(video)
    mapa_a = ["-map", "0:a?"]
    if audio and (musica or vel != 1.0):
        a = f"[0:a]atempo={vel}[a0]" if vel != 1.0 else "[0:a]anull[a0]"
        if musica:
            vol = float((e.get("musica") or {}).get("volumen", 0.12))
            a += f";[1:a]volume={vol}[am];[a0][am]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]"
        else:
            a += ";[a0]anull[a]"
        v += ";" + a
        mapa_a = ["-map", "[a]"]
    args = [ffmpeg(), "-y", *entradas, "-filter_complex", v, "-map", "[v]", *mapa_a, "-c:v", "libx264",
            "-preset", "medium", "-crf", str(int(e.get("calidad_crf", 20))), "-maxrate", "3000k", "-bufsize", "6000k",
            "-r", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
            str(out)]
    rc, o, err = run(args)
    if rc != 0:
        log(f"ERROR render {out.name}: {err[-700:]}")
        return None
    return modo


def guardar_meta(out, cl, d, base, modo):
    meta = {k: cl[k] for k in ("titulo", "descripcion", "hashtags", "ini", "fin")}
    # los momentos virales van sueltos (sin "Part N"); los cortes secuenciales sí numeran
    meta.update({"video": d["video"], "fichero": out.name, "parte": cl["n"], "encuadre": modo,
                 "partes": 1 if cl.get("suelto") else len(d["clips"]), "gancho": cl.get("gancho", "")})
    org = (estado().get("origen") or {}).get(base)
    if org:
        meta["credito"] = {"canal": org.get("canal"), "url": org.get("url"), "cc": org.get("tipo") == "cc"}
    j = out.with_suffix(".json")
    if j.exists():  # al rehacer, conservar lo ya apuntado
        viejo = json.loads(j.read_text(encoding="utf-8"))
        meta = {**viejo, **meta}
    j.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def sin_subir(out):
    j = out.with_suffix(".json")
    try:
        return not json.loads(j.read_text(encoding="utf-8")).get("subido")
    except Exception:
        return True


def previa(c, e):
    """Un solo clip en previas/<cuenta>.mp4 + 3 fotogramas, para revisar el estilo sin tocar la cola."""
    cjs = sorted(TRABAJO.glob("*.clips.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for cj in cjs:
        d = json.loads(cj.read_text(encoding="utf-8"))
        video = FUENTES / d["video"]
        if d["clips"] and video.exists():
            break
    else:
        sys.exit("No hay ningún clip cortado todavía para esta cuenta: ejecuta antes `python clips.py procesar --cuenta "
                 f"{CUENTA}` (o pon un vídeo en fuentes.carpeta_local).")
    n = int(next((sys.argv[i + 1] for i, x in enumerate(sys.argv) if x == "--clip"), 1))
    cl = d["clips"][min(n, len(d["clips"])) - 1]
    carpeta = RAIZ / "previas"; carpeta.mkdir(exist_ok=True)
    out = carpeta / f"{CUENTA}.mp4"
    modo = render_clip(c, e, video, cl, out, f"previa_{CUENTA}")
    if not modo:
        sys.exit(1)
    dur = cl["fin"] - cl["ini"]
    for i, t in enumerate((1.5, dur / 2, max(dur - 2, 0)), 1):
        run([ffmpeg(), "-y", "-ss", f"{t:.2f}", "-i", str(out), "-frames:v", "1", "-q:v", "3",
             str(carpeta / f"{CUENTA}_{i}.jpg")])
    log(f"Previa lista: {out} ({modo}) + {CUENTA}_1..3.jpg · «{cl['titulo']}» · gancho «{cl.get('gancho', '')}»")


def main():
    c = cfg()
    e = estilo(c)
    if "--previa" in sys.argv:
        return previa(c, e)
    rehacer = "--rehacer" in sys.argv
    for cj in sorted(TRABAJO.glob("*.clips.json")):
        d = json.loads(cj.read_text(encoding="utf-8"))
        video = FUENTES / d["video"]
        if not video.exists():
            log(f"Falta el vídeo {video.name}"); continue
        base = cj.name.replace(".clips.json", "")
        for cl in d["clips"]:
            nombre = f"{base}_{cl['n']:02d}"
            out = LISTOS / f"{nombre}.mp4"
            if (LISTOS.parent / "subidos" / out.name).exists():
                continue
            if out.exists() and not (rehacer and sin_subir(out)):
                continue
            modo = render_clip(c, e, video, cl, out, nombre)
            if modo:
                guardar_meta(out, cl, d, base, modo)
                log(f"Listo {out.name} ({cl['fin'] - cl['ini']:.0f}s, {modo}) · {cl['titulo']}")


if __name__ == "__main__":
    main()
