# -*- coding: utf-8 -*-
"""Reencuadre vertical 9:16 siguiendo caras (técnica de los clones open source de Opus Clip, hecha con OpenCV YuNet):
  1 cara dominante  -> "seguir": recorte vertical a pantalla completa que sigue la cara con suavizado (EMA + zona muerta)
  2 caras separadas -> "dividir": las dos personas apiladas (arriba / abajo), típico de pódcast
  sin caras claras  -> "blur": vídeo centrado sobre fondo difuminado (como antes)
Devuelve el trozo de filtro ffmpeg que deja la imagen 1080x1920 en [v]."""
from pathlib import Path

import cv2

from comun import RAIZ

MODELO = RAIZ / "modelos" / "face_detection_yunet_2023mar.onnx"
MUESTRAS_SEG = 4          # análisis a 4 fotogramas por segundo
ANCHO_ANALISIS = 640


def caras(video, ini, dur):
    """Lista por muestra: (t, [(cx, cy, w, h, score)]) en coordenadas normalizadas 0-1."""
    cap = cv2.VideoCapture(str(video))
    W = cap.get(cv2.CAP_PROP_FRAME_WIDTH); H = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if not W or not H:
        return [], 0, 0
    esc = ANCHO_ANALISIS / W
    w2, h2 = int(W * esc), int(H * esc)
    det = cv2.FaceDetectorYN.create(str(MODELO), "", (w2, h2), score_threshold=0.75)
    out = []
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    paso = max(1, int(round(fps / MUESTRAS_SEG)))
    cap.set(cv2.CAP_PROP_POS_MSEC, ini * 1000)  # un solo salto y luego lectura seguida (saltar en cada muestra es lentísimo)
    n = 0
    t = 0.0
    while t < dur:
        for _ in range(paso - 1):
            if not cap.grab():
                break
        ok, frame = cap.read()
        if not ok:
            break
        n += paso
        frame = cv2.resize(frame, (w2, h2))
        _, res = det.detect(frame)
        lista = []
        for r in (res if res is not None else []):
            x, y, w, h, score = r[0], r[1], r[2], r[3], r[-1]
            if w / w2 < 0.04:  # caras diminutas (público, fondo): fuera
                continue
            lista.append(((x + w / 2) / w2, (y + h / 2) / h2, w / w2, h / h2, float(score)))
        out.append((t, sorted(lista, key=lambda c: -c[2])))
        t = n / fps
    cap.release()
    return out, W, H


def decidir(muestras):
    """Elige el modo y los centros horizontales (normalizados)."""
    if not muestras:
        return "blur", []
    con_cara = [m for m in muestras if m[1]]
    if len(con_cara) < 0.45 * len(muestras):
        return "blur", []
    # dos personas a la vez, bien separadas, en buena parte del clip -> dividir
    dobles = [m for m in con_cara if len(m[1]) >= 2 and abs(m[1][0][0] - m[1][1][0]) > 0.28]
    if len(dobles) > 0.5 * len(con_cara):
        izq = sorted(min(c[0] for c in m[1][:2]) for m in dobles)
        der = sorted(max(c[0] for c in m[1][:2]) for m in dobles)
        ys = sorted(c[1] for m in dobles for c in m[1][:2])
        return "dividir", [izq[len(izq) // 2], der[len(der) // 2], ys[len(ys) // 2]]
    return "seguir", []


def trayectoria(muestras, W, H, cw):
    """x del recorte (px) por muestra: sigue la cara más grande, con EMA y zona muerta para que no tiemble."""
    xs, actual, ultimo = [], None, 0.5
    for t, lista in muestras:
        objetivo = lista[0][0] if lista else ultimo
        ultimo = objetivo
        if actual is None:
            actual = objetivo
        elif abs(objetivo - actual) > 0.25:   # cambio de plano / de persona: salto directo
            actual = objetivo
        elif abs(objetivo - actual) > 0.03:   # zona muerta: movimientos pequeños no mueven la cámara
            actual += (objetivo - actual) * 0.18
        x = min(max(actual * W - cw / 2, 0), W - cw)
        xs.append((t, int(round(x / 2) * 2)))
    return xs


def ruta_ffmpeg(p):
    return str(p).replace("\\", "/").replace(":", "\\:")


def filtro(video, ini, dur, cmds_path, forzado=None):
    """Trozo de -filter_complex que produce [v] (1080x1920) y el modo usado.
    forzado="seguir" sigue siempre a la cara principal (centro si no hay caras) en vez de decidir solo."""
    muestras, W, H = caras(video, ini, dur)
    modo, info = decidir(muestras)
    if forzado == "seguir" and muestras:
        modo = "seguir"
    if modo == "seguir":
        cw = int(H * 9 / 16) // 2 * 2
        if cw >= W:
            modo = "blur"
        else:
            xs = trayectoria(muestras, W, H, cw)
            lineas, previo = [], None
            for t, x in xs:
                if x != previo:
                    lineas.append(f"{t:.2f} crop x {x};")
                    previo = x
            Path(cmds_path).write_text("\n".join(lineas) + "\n", encoding="utf-8")
            x0 = xs[0][1] if xs else int((W - cw) / 2)
            return (f"[0:v]sendcmd=f='{ruta_ffmpeg(cmds_path)}',crop=w={cw}:h={int(H)}:x={x0}:y=0,"
                    f"scale=1080:1920,setsar=1[v]"), modo
    if modo == "dividir":
        cx1, cx2, cy = info
        cw = int(min(W / 2, H * 1.125)) // 2 * 2       # cada mitad: proporción 1080x960
        ch = int(cw / 1.125) // 2 * 2
        def caja(cx):
            x = int(min(max(cx * W - cw / 2, 0), W - cw)) // 2 * 2
            y = int(min(max(cy * H - ch * 0.45, 0), H - ch)) // 2 * 2
            return x, y
        (x1, y1), (x2, y2) = caja(cx1), caja(cx2)
        return (f"[0:v]split=2[s1][s2];[s1]crop={cw}:{ch}:{x1}:{y1},scale=1080:960,setsar=1[t];"
                f"[s2]crop={cw}:{ch}:{x2}:{y2},scale=1080:960,setsar=1[b];[t][b]vstack[v]"), modo
    return ("[0:v]split=2[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:10[bg];"
            "[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"), "blur"
