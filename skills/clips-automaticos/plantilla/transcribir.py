# -*- coding: utf-8 -*-
"""Transcribe cada vídeo de cuentas/<cuenta>/fuentes/ con faster-whisper (timestamps por palabra) a trabajo/<nombre>.palabras.json.
Uso: python transcribir.py"""
import json
from pathlib import Path

from comun import FUENTES, TRABAJO, cfg, log


def _dlls_cuda():
    """Windows no encuentra las DLL de nvidia-cublas/cudnn instaladas por pip: se registran a mano."""
    import os
    import site
    if os.name != "nt":
        return
    for sp in site.getsitepackages():
        for bin_ in Path(sp, "nvidia").glob("*/bin"):
            os.add_dll_directory(str(bin_))
            os.environ["PATH"] = str(bin_) + os.pathsep + os.environ.get("PATH", "")


def _parche_av():
    """faster-whisper 1.2 llama a av.open(metadata_errors=...), argumento que PyAV 15+ ya no acepta."""
    import av
    original = av.open
    if getattr(original, "_parcheado", False):
        return

    def abrir(*a, **kw):
        kw.pop("metadata_errors", None)
        return original(*a, **kw)
    abrir._parcheado = True
    av.open = abrir


def modelo(c):
    _dlls_cuda()
    _parche_av()
    from faster_whisper import WhisperModel
    disp = c.get("whisper_dispositivo", "auto")
    nombre = c.get("whisper_modelo", "small")
    if disp in ("auto", "cuda"):
        try:
            m = WhisperModel(nombre, device="cuda", compute_type="float16")
            log(f"Whisper {nombre} en GPU")
            return m
        except Exception as e:
            if disp == "cuda":
                raise
            log(f"GPU no disponible ({type(e).__name__}); uso CPU")
    m = WhisperModel(nombre, device="cpu", compute_type="int8")
    log(f"Whisper {nombre} en CPU")
    return m


def _audio(v, seg):
    """Un trozo de audio del centro del vídeo (el principio suele ser música o intro)."""
    from faster_whisper.audio import decode_audio
    a = decode_audio(str(v))
    medio = len(a) // 2
    return a[max(0, medio - seg * 8000): medio + seg * 8000]


def main():
    c = cfg()
    videos = [p for p in FUENTES.iterdir() if p.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov", ".m4a", ".mp3")]
    pendientes = [v for v in videos if not (TRABAJO / f"{v.stem}.palabras.json").exists()]
    if not pendientes:
        log("Nada que transcribir")
        return
    m = modelo(c)
    idioma = None if c.get("idioma", "auto") == "auto" else c.get("idioma")
    for v in pendientes:
        log(f"Transcribiendo {v.name}")
        if idioma:  # comprobar que el audio está en el idioma pedido (las búsquedas traen mucho vídeo en otros idiomas)
            detectado, prob, _ = m.detect_language(audio=_audio(v, 30))
            if detectado != idioma:
                log(f"  descartado: el audio está en '{detectado}' ({prob:.0%}), no en '{idioma}'")
                (TRABAJO / f"{v.stem}.palabras.json").write_text(json.dumps(
                    {"video": v.name, "idioma": detectado, "descartado": True, "palabras": []}), encoding="utf-8")
                continue
        segs, info = m.transcribe(str(v), language=idioma, word_timestamps=True, vad_filter=True)
        palabras = []
        for s in segs:
            for w in (s.words or []):
                palabras.append({"w": w.word.strip(), "ini": round(w.start, 2), "fin": round(w.end, 2)})
        (TRABAJO / f"{v.stem}.palabras.json").write_text(
            json.dumps({"video": v.name, "idioma": info.language, "dur": round(info.duration, 1), "palabras": palabras},
                       ensure_ascii=False), encoding="utf-8")
        log(f"  {len(palabras)} palabras, {info.duration:.0f} s")


if __name__ == "__main__":
    main()
