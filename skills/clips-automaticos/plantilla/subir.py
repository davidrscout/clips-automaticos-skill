# -*- coding: utf-8 -*-
"""Sube los clips de cuentas/<cuenta>/listos a TikTok y YouTube Shorts con Playwright, usando el perfil de Chrome
donde está la sesión de cada red (config: redes.<red>.perfil -> perfiles/<perfil>, sesión iniciada una vez con login).
  python subir.py                   todas las cuentas: sube lo que toque (cupo diario y franjas en la hora de su público)
  python subir.py --ahora N         sube N clips ya, sin mirar horas (prueba)
  python subir.py --cuenta mi_cuenta --red tiktok --ahora 1
  python subir.py --login           abre los perfiles de Chrome (sin automatizar) para iniciar sesión
  python subir.py --comprobar       dice si cada red abre la cuenta correcta
Cada clip lleva un .json con título/descripción/hashtags; ahí se apunta en qué redes y cuándo se subió."""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import time

from comun import (CUENTA, LISTOS, LOGS, RAIZ, SUBIDOS, ahora, avisar_telegram, candado, cfg, chrome_exe, cuentas_activas,
                   en_cuentas, estilo, log)

ARGS_CHROME = ["--disable-blink-features=AutomationControlled", "--no-first-run", "--no-default-browser-check",
               "--disable-infobars", "--window-size=1400,950"]
PARTE = {"es": "Parte", "en": "Part", "pt": "Parte", "fr": "Partie", "it": "Parte", "de": "Teil"}


def perfil_de(c, red):
    """Carpeta del perfil de Chrome donde está la sesión de esa red (config: redes.<red>.perfil)."""
    p = ((c.get("redes") or {}).get(red) or {}).get("perfil")
    return f"perfiles/{p or c['cuenta']}"


def contexto(pw, c, visible=True, perfil=None):
    perfil = RAIZ / (perfil or f"perfiles/{c['cuenta']}")
    perfil.mkdir(parents=True, exist_ok=True)
    exe = chrome_exe(c)
    kw = dict(user_data_dir=str(perfil), headless=not visible, args=ARGS_CHROME, viewport={"width": 1380, "height": 900},
              locale=c.get("idioma_navegador", "es-ES"), ignore_default_args=["--enable-automation"])
    if exe:
        kw["executable_path"] = exe
    else:
        kw["channel"] = "chrome"
    return pw.chromium.launch_persistent_context(**kw)


def captura(page, nombre):
    try:
        f = LOGS / f"{datetime.datetime.now():%Y%m%d_%H%M%S}_{CUENTA}_{nombre}.png"
        page.screenshot(path=str(f))
        log(f"  captura: {f.name}")
    except Exception:
        pass


def titulo_de(meta, maximo):
    palabra = PARTE.get(str(cfg().get("idioma", "en")).split("-")[0], "Part")
    parte = f" ({palabra} {meta['parte']})" if meta.get("partes", 1) > 1 else ""
    return meta["titulo"][: maximo - len(parte)].rstrip() + parte


def credito_de(meta, c):
    """Línea de crédito al autor original (obligatoria con licencia CC BY). Se apaga con estilo.textos.credito: false."""
    t = estilo(c)["textos"]
    cr = meta.get("credito") or {}
    if not cr.get("canal") or (not t.get("credito", True) and not cr.get("cc")):
        return ""
    linea = str(t.get("plantilla_credito") or "Source: {canal} — {url}").format(canal=cr["canal"], url=cr.get("url", ""))
    return linea + (" (CC BY)" if cr.get("cc") else "")


def sin_sesion(page, red):
    url = page.url.lower()
    if red == "youtube":
        return "accounts.google.com" in url or "signin" in url
    if "/login" in url:
        return True
    try:  # TikTok Studio enseña el login sin cambiar la URL
        return page.locator("text=/Inicia sesión en TikTok|Log in to TikTok/i").count() > 0
    except Exception:
        return False


def usuario_tiktok(page):
    """@usuario con sesión en este perfil (enlace «Perfil» de la barra lateral)."""
    page.goto("https://www.tiktok.com/foryou", wait_until="domcontentloaded"); time.sleep(6)
    for a in page.locator("a[href*='/@']").all()[:40]:
        h = a.get_attribute("href") or ""
        t = ((a.get_attribute("data-e2e") or "") + (a.inner_text() or "")).lower()
        if "profile" in t or "perfil" in t:
            return h.split("/@")[1].split("?")[0].split("/")[0]
    return ""


def verificar_cuenta(page, red, c):
    """No publicar nunca en una cuenta que no sea la configurada."""
    rc = (c.get("redes") or {}).get(red) or {}
    if red == "tiktok" and rc.get("usuario"):
        u = usuario_tiktok(page) or usuario_tiktok(page)  # 2º intento si la página tardó en cargar
        if u.lower() != rc["usuario"].lower():
            raise RuntimeError(f"CUENTA EQUIVOCADA: en este perfil está @{u or '¿sin sesión?'}, se esperaba @{rc['usuario']}")
    if red == "youtube" and rc.get("canal"):
        page.goto(url_subida_youtube(c), wait_until="domcontentloaded"); time.sleep(5)
        if rc["canal"] not in page.url:
            raise RuntimeError(f"CUENTA EQUIVOCADA: YouTube no abre el canal {rc['canal']} en este perfil ({page.url[:80]})")


# ------------------------------------------------------------------ YouTube
def url_subida_youtube(c):
    canal = ((c.get("redes") or {}).get("youtube") or {}).get("canal")
    # con el ID del canal se sube SIEMPRE a ese canal, aunque la cuenta tenga varios
    return f"https://studio.youtube.com/channel/{canal}/videos/upload?d=ud" if canal else "https://www.youtube.com/upload"


def subir_youtube(page, mp4, meta, c):
    page.goto(url_subida_youtube(c), wait_until="domcontentloaded")
    page.wait_for_selector("input[type=file]", state="attached", timeout=60000)
    page.set_input_files("input[type=file]", str(mp4))
    titulo = page.locator("#title-textarea #textbox, #title-textbox #textbox").first
    titulo.wait_for(timeout=90000)
    time.sleep(2)
    titulo.click(); page.keyboard.press("Control+A"); page.keyboard.type(titulo_de(meta, 90) + " #Shorts", delay=10)
    descr = page.locator("#description-textarea #textbox, #description-textbox #textbox").first
    descr.click(); page.keyboard.press("Control+A")
    partes = (meta["descripcion"], credito_de(meta, c), " ".join(meta.get("hashtags", [])))
    page.keyboard.type("\n\n".join(x for x in partes if x)[:4500], delay=5)
    nk = page.locator("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']").first
    nk.scroll_into_view_if_needed(); nk.wait_for(timeout=30000); nk.click()
    for _ in range(3):
        page.locator("#next-button").first.click(); time.sleep(1.5)
    page.locator("tp-yt-paper-radio-button[name='PUBLIC']").first.click()
    fin = time.time() + 900
    while time.time() < fin:  # esperar a que acabe la SUBIDA (no hace falta esperar a las comprobaciones)
        loc = page.locator("ytcp-video-upload-progress .progress-label, span.progress-label")
        txt = loc.first.inner_text(timeout=5000) if loc.count() else ""
        if any(k in txt.lower() for k in ("subida completa", "upload complete", "comprob", "check", "procesad", "processed")):
            break
        time.sleep(3)
    page.locator("#done-button").first.click()
    enlace = ""
    try:
        a = page.locator("ytcp-video-info a.ytcp-video-info, a[href*='youtube.com/shorts/'], a[href*='youtu.be/']").first
        a.wait_for(timeout=30000)
        enlace = a.get_attribute("href") or a.inner_text()
    except Exception:
        pass
    for sel in ("ytcp-button#close-button", "#close-button"):
        try:
            if page.locator(sel).count():
                page.locator(sel).first.click(timeout=3000); break
        except Exception:
            pass
    return enlace


# ------------------------------------------------------------------ TikTok
def cerrar_avisos_tiktok(page):
    """Avisos que TikTok Studio saca encima del editor. Las revisiones automáticas de contenido se ACTIVAN
    (comprueban derechos de autor antes de publicar)."""
    for nombre in ("Activar", "Turn on", "Entendido", "Got it", "Aceptar", "OK"):
        for b in page.get_by_role("button", name=nombre, exact=True).all():
            try:
                if b.is_visible():
                    b.click(timeout=2000); time.sleep(1)
            except Exception:
                pass


def subir_tiktok(page, mp4, meta, c):
    page.goto("https://www.tiktok.com/tiktokstudio/upload?from=creator_center", wait_until="domcontentloaded")
    page.wait_for_selector("input[type=file]", state="attached", timeout=60000)
    page.set_input_files("input[type=file]", str(mp4))
    ed = page.locator(".public-DraftEditor-content[contenteditable='true'], div[contenteditable='true']").first
    ed.wait_for(timeout=120000)
    time.sleep(3)
    cerrar_avisos_tiktok(page)
    ed.click(); page.keyboard.press("Control+A"); page.keyboard.press("Delete")
    cr = (meta.get("credito") or {}).get("canal") if credito_de(meta, c) else ""
    texto = (titulo_de(meta, 150) + (f" · Credit: {cr}" if cr else "") + " " + " ".join(meta.get("hashtags", [])))[:2000]
    for trozo in texto.split(" "):
        page.keyboard.type(trozo + " ", delay=15)
        if trozo.startswith("#"):
            time.sleep(0.8); page.keyboard.press("Escape")
    btn = page.locator("button[data-e2e='post_video_button']").first
    if not btn.count():
        btn = page.locator("button:has-text('Publicar'), button:has-text('Post')").last
    fin = time.time() + 900
    while time.time() < fin:  # el botón se habilita cuando el vídeo termina de subir
        try:
            if btn.is_enabled() and btn.get_attribute("data-disabled") != "true" and btn.get_attribute("aria-disabled") != "true":
                break
        except Exception:
            pass
        time.sleep(3)
    cerrar_avisos_tiktok(page)
    btn.click()
    time.sleep(3)
    for sel in ("button:has-text('Publicar ahora')", "button:has-text('Post now')"):
        try:
            if page.locator(sel).count():
                page.locator(sel).first.click(timeout=3000); break
        except Exception:
            pass
    # éxito = TikTok nos saca del editor (va a la lista de publicaciones) o muestra el aviso de publicado
    fin = time.time() + 120
    while time.time() < fin:
        if "/upload" not in page.url or page.locator("text=/publicado|posted|Tu vídeo se está publicando|being uploaded/i").count():
            return ""
        time.sleep(2)
    raise RuntimeError("TikTok no confirmó la publicación")


SUBIDORES = {"youtube": subir_youtube, "tiktok": subir_tiktok}


# ------------------------------------------------------------------ cola
def leer(j):
    try:
        return json.loads(j.read_text(encoding="utf-8"))
    except Exception:
        return None


def pendientes(red):
    orden = lambda f: (f.with_suffix(".mp4").stat().st_mtime if f.with_suffix(".mp4").exists() else 0, f.name)
    out = []
    for j in sorted(LISTOS.glob("*.json"), key=orden):
        m = leer(j)
        if m is None or red in (m.get("subido") or {}):
            continue
        mp4 = j.with_suffix(".mp4")
        if mp4.exists():
            out.append((mp4, j, m))
    return out


def subidos_hoy(red, c):
    """(número, franjas usadas) hoy en la hora de la cuenta."""
    hoy = ahora(c).date().isoformat()
    n, franjas = 0, set()
    for carpeta in (LISTOS, SUBIDOS):
        for j in carpeta.glob("*.json"):
            m = leer(j) or {}
            if str((m.get("subido_local") or {}).get(red, "")).startswith(hoy):
                n += 1
                franjas.add((m.get("franjas") or {}).get(red))
    return n, franjas


def toca_ahora(horas, usadas, c):
    """La franja más reciente de hoy (en la hora de la cuenta) que ya ha llegado y no se ha usado."""
    t = ahora(c)
    for h in sorted(horas or [], reverse=True):
        hh, mm = (int(x) for x in str(h).split(":"))
        inicio = t.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if inicio <= t and h not in usadas:
            return h
    return None


def marcar(j, m, red, c, franja=None, enlace=""):
    m.setdefault("subido", {})[red] = datetime.datetime.now().isoformat(timespec="seconds")
    m.setdefault("subido_local", {})[red] = ahora(c).isoformat(timespec="seconds")
    if franja:
        m.setdefault("franjas", {})[red] = franja
    if enlace:
        m.setdefault("urls", {})[red] = enlace
    j.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    activas = [r for r, v in (c.get("redes") or {}).items() if v.get("activo")]
    if all(r in m["subido"] for r in activas):
        for f in (j, j.with_suffix(".mp4")):
            shutil.move(str(f), str(SUBIDOS / f.name))


def plan(c, a):
    """Qué subir en cada red ANTES de abrir Chrome (si no toca nada, no se abre)."""
    out = []
    for red, rc in (c.get("redes") or {}).items():
        if not rc.get("activo") or red not in SUBIDORES or (a.red and a.red != red):
            continue
        cola = pendientes(red)
        if not cola:
            log(f"{red}: cola vacía")
            continue
        if a.ahora:
            out.append((red, None, cola[:a.ahora])); continue
        n, usadas = subidos_hoy(red, c)
        franja = toca_ahora(rc.get("horas"), usadas, c)
        if not franja or n >= int(rc.get("por_dia", 1)):
            continue
        out.append((red, franja, cola[:1]))
    return out


# ------------------------------------------------------------------ login / comprobación
def login_todas(cuentas):
    """Chrome normal (sin Playwright, Google no bloquea el login) con cada perfil que usan las cuentas."""
    perfiles = sorted({perfil_de(cfg(cu), r) for cu in cuentas for r, v in (cfg(cu).get("redes") or {}).items()
                       if (v or {}).get("activo")})
    exe = chrome_exe(cfg(cuentas[0]))
    if not exe:
        sys.exit("No encuentro Chrome: pon su ruta en config.yaml -> chrome_exe")
    quien = {}
    for cu in cuentas:
        for r, v in (cfg(cu).get("redes") or {}).items():
            if (v or {}).get("activo"):
                quien.setdefault(perfil_de(cfg(cu), r), []).append(f"{r} de {cu}")
    procs = []
    for p in perfiles:
        carpeta = RAIZ / p
        carpeta.mkdir(parents=True, exist_ok=True)
        nombre = p.split("/")[-1].upper()
        aviso = (f"data:text/html,<title>PERFIL {nombre}</title><h1 style='font:40px sans-serif'>Perfil {nombre}</h1>"
                 f"<p style='font:24px sans-serif'>Inicia sesión aquí en: {', '.join(quien.get(p, []))}</p>")
        procs.append(subprocess.Popen([exe, f"--user-data-dir={carpeta}", "--no-first-run", "--no-default-browser-check",
                                       "--new-window", aviso,
                                       "https://accounts.google.com/ServiceLogin?continue=https://studio.youtube.com/",
                                       "https://www.tiktok.com/login"]))
    print("Inicia sesión en cada ventana (la 1ª pestaña dice qué cuentas van en ese perfil) y CIÉRRALAS al acabar.")
    for pr in procs:
        pr.wait()
    en_cuentas("subir.py", ["--comprobar"], cuentas)  # comprueba canal y usuario de cada cuenta


def comprobar(c):
    from playwright.sync_api import sync_playwright
    res = {}
    with sync_playwright() as pw:
        for red in ("youtube", "tiktok"):
            if not ((c.get("redes") or {}).get(red) or {}).get("activo"):
                continue
            ctx = contexto(pw, c, perfil=perfil_de(c, red))
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            try:
                verificar_cuenta(page, red, c)
                res[red] = "OK"
            except Exception as e:
                res[red] = str(e)[:120]
            ctx.close()
    log("Cuentas: " + " | ".join(f"{r}: {v}" for r, v in res.items()))
    return res


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true")
    ap.add_argument("--comprobar", action="store_true")
    ap.add_argument("--ahora", type=int, default=0, help="sube N clips ya, sin mirar horarios")
    ap.add_argument("--red", default="")
    ap.add_argument("--cuenta", default="")
    ap.add_argument("--oculto", action="store_true", help="Chrome sin ventana (TikTok suele bloquearlo)")
    a = ap.parse_args()

    lock = candado(f"subir_{os.environ.get('CLIPS_CUENTA', 'todas')}")
    if lock is None:  # otra subida (tarea horaria o manual) en marcha: no duplicar vídeos
        log("Otra subida en marcha, salgo"); return
    if "CLIPS_CUENTA" not in os.environ:  # proceso padre: repartir por cuentas
        cuentas = [a.cuenta] if a.cuenta else cuentas_activas()
        if not cuentas:
            sys.exit("No hay cuentas activas en config.yaml")
        if a.login:
            return login_todas(cuentas)
        args = [x for x in sys.argv[1:]]
        return en_cuentas("subir.py", args, cuentas)

    c = cfg()
    if a.comprobar:
        comprobar(c); return
    tareas = plan(c, a)
    if not tareas:
        return
    from playwright.sync_api import sync_playwright
    hechas, fallos = [], []
    with sync_playwright() as pw:
        for red, franja, cola in tareas:
            ctx = None
            for intento in range(3):  # Chrome a veces se cierra al arrancar: reintentar
                try:
                    ctx = contexto(pw, c, visible=not a.oculto, perfil=perfil_de(c, red))
                    break
                except Exception as e:
                    log(f"{red}: Chrome no arrancó (intento {intento + 1}): {str(e)[:120]}"); time.sleep(10)
            if ctx is None:
                fallos.append(f"{red}: Chrome no arranca"); continue
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            try:
                verificar_cuenta(page, red, c)
            except Exception as e:
                log(f"{red}: {e}"); fallos.append(f"{red}: {e}"); captura(page, f"cuenta_{red}"); ctx.close()
                continue
            for mp4, j, m in cola:
                log(f"{red}: subiendo {mp4.name} · {m['titulo']}")
                try:
                    enlace = SUBIDORES[red](page, mp4, m, c)
                    marcar(j, m, red, c, franja, enlace)
                    hechas.append(f"{red}: {m['titulo']} {enlace}")
                    log(f"{red}: OK {mp4.name} {enlace}")
                except Exception as e:
                    motivo = "SIN SESIÓN: ejecuta python clips.py login" if sin_sesion(page, red) else f"{type(e).__name__}: {str(e)[:200]}"
                    log(f"{red}: ERROR {mp4.name}: {motivo}")
                    fallos.append(f"{red}: {motivo}")
                    captura(page, f"error_{red}")
                    break
                time.sleep(5)
            ctx.close()
    if hechas or fallos:
        avisar_telegram("Clips:\n" + "\n".join(hechas + ["FALLO " + f for f in fallos]))


if __name__ == "__main__":
    main()
