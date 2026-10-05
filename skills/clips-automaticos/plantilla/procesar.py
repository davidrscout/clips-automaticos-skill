# -*- coding: utf-8 -*-
"""Prepara clips para todas las cuentas activas (o la de --cuenta):
  buscar -> descargar -> transcribir -> cortar -> render
Uso: python procesar.py [--cuenta X]"""
import os
import sys
import traceback

from comun import avisar_telegram, candado, cuentas_activas, en_cuentas, log


def main():
    lock = candado(f"procesar_{os.environ.get('CLIPS_CUENTA', 'todas')}")
    if lock is None:
        log("Otro procesado en marcha, salgo"); return
    if "CLIPS_CUENTA" not in os.environ:
        cuentas = [sys.argv[sys.argv.index("--cuenta") + 1]] if "--cuenta" in sys.argv else cuentas_activas()
        return en_cuentas("procesar.py", [], cuentas)
    import buscar, cortar, descargar, render, transcribir
    for paso in (buscar, descargar, transcribir, cortar, render):
        try:
            paso.main()
        except SystemExit as e:
            log(f"{paso.__name__}: {e}"); avisar_telegram(f"Clips: falló {paso.__name__}: {e}"); return
        except Exception:
            log(f"ERROR en {paso.__name__}:\n{traceback.format_exc()}")
            avisar_telegram(f"Clips: falló {paso.__name__} (mira logs/clips.log)")
            return


if __name__ == "__main__":
    main()
