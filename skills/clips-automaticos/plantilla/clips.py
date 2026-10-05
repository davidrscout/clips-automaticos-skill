# -*- coding: utf-8 -*-
"""Punto de entrada único. Ejecutar siempre con el python del venv:
  Windows: venv\\Scripts\\python clips.py <orden>      Mac/Linux: venv/bin/python clips.py <orden>

  procesar   [--cuenta X]                  busca, descarga, transcribe, corta y renderiza
  subir      [--cuenta X] [--red tiktok|youtube] [--ahora N]   sube lo que toque (o N ya, sin mirar horas)
  login                                     abre los perfiles de Chrome para iniciar sesión una vez
  comprobar  [--cuenta X]                   verifica que cada red abre la cuenta correcta
  previa     --cuenta X [--clip N]          renderiza 1 clip con el estilo actual en previas/ (+ 3 fotogramas .jpg)
  rehacer    --cuenta X                     vuelve a renderizar con el estilo actual los clips aún no subidos
  estado                                    clips en cola y subidos hoy por cuenta y red
  programar / desprogramar                  tareas automáticas (Windows: Programador de tareas; Mac/Linux: crontab)"""
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PY = sys.executable


def con_cuenta(cuenta, script, args):
    env = {**os.environ, "CLIPS_CUENTA": cuenta, "PYTHONIOENCODING": "utf-8"}
    return subprocess.call([PY, str(RAIZ / script), *args], env=env, cwd=str(RAIZ))


def arg(nombre, defecto=None):
    return sys.argv[sys.argv.index(nombre) + 1] if nombre in sys.argv else defecto


def estado():
    from comun import cfg, cuentas_activas
    import datetime
    for cu in cuentas_activas():
        c = cfg(cu)
        base = RAIZ / "cuentas" / cu
        hoy = datetime.date.today().isoformat()
        print(f"\n== {cu} ==")
        for red, rc in (c.get("redes") or {}).items():
            if not rc.get("activo"):
                continue
            cola = hoy_n = 0
            for carpeta in ("listos", "subidos"):
                for j in (base / carpeta).glob("*.json"):
                    try:
                        m = json.loads(j.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    if red not in (m.get("subido") or {}):
                        cola += carpeta == "listos"
                    elif str((m.get("subido_local") or {}).get(red, "")).startswith(hoy):
                        hoy_n += 1
            print(f"  {red:8} en cola: {cola:3}   subidos hoy: {hoy_n}/{rc.get('por_dia', 1)}")


def programar():
    if os.name == "nt":
        pw = Path(PY).with_name("pythonw.exe")
        ps = (f"$d='{RAIZ}'; $pw='{pw}'; "
              "$a=New-ScheduledTaskAction -Execute $pw -Argument 'procesar.py' -WorkingDirectory $d; "
              "$t=New-ScheduledTaskTrigger -Once -At 00:30 -RepetitionInterval (New-TimeSpan -Hours 4) -RepetitionDuration (New-TimeSpan -Days 3650); "
              "$s=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 3) -StartWhenAvailable -MultipleInstances IgnoreNew; "
              "Register-ScheduledTask -TaskName 'Clips-Procesar' -Action $a -Trigger $t -Settings $s -RunLevel Limited -Force | Out-Null; "
              "$a2=New-ScheduledTaskAction -Execute $pw -Argument 'subir.py' -WorkingDirectory $d; "
              "$t2=New-ScheduledTaskTrigger -Once -At 00:05 -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Days 3650); "
              "$s2=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 50) -StartWhenAvailable -MultipleInstances IgnoreNew; "
              "Register-ScheduledTask -TaskName 'Clips-Subir' -Action $a2 -Trigger $t2 -Settings $s2 -RunLevel Limited -Force | Out-Null; "
              "'Tareas creadas: Clips-Procesar (cada 4 h) y Clips-Subir (cada 30 min).'")
        return subprocess.call(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps])
    lineas = [f"30 */4 * * * cd '{RAIZ}' && '{PY}' procesar.py >> logs/cron.log 2>&1  # clips-auto",
              f"5,35 * * * * cd '{RAIZ}' && '{PY}' subir.py >> logs/cron.log 2>&1  # clips-auto"]
    actual = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    nuevo = "\n".join([l for l in actual.splitlines() if "# clips-auto" not in l] + lineas) + "\n"
    subprocess.run(["crontab", "-"], input=nuevo, text=True, check=True)
    print("crontab actualizado (procesar cada 4 h, subir cada 30 min). Ojo: subir necesita sesión gráfica abierta.")


def desprogramar():
    if os.name == "nt":
        for t in ("Clips-Procesar", "Clips-Subir"):
            subprocess.call(["schtasks", "/delete", "/tn", t, "/f"])
        return
    actual = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    nuevo = "\n".join(l for l in actual.splitlines() if "# clips-auto" not in l) + "\n"
    subprocess.run(["crontab", "-"], input=nuevo, text=True, check=True)
    print("Tareas de clips quitadas del crontab.")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "ayuda"):
        print(__doc__); return
    orden, resto = sys.argv[1], sys.argv[2:]
    cuenta = arg("--cuenta")
    if orden == "procesar":
        return subprocess.call([PY, str(RAIZ / "procesar.py"), *resto], cwd=str(RAIZ))
    if orden in ("subir", "login", "comprobar"):
        extra = {"login": ["--login"], "comprobar": ["--comprobar"]}.get(orden, [])
        return subprocess.call([PY, str(RAIZ / "subir.py"), *extra, *resto], cwd=str(RAIZ))
    if orden in ("previa", "rehacer"):
        if not cuenta:
            sys.exit(f"Falta --cuenta (ej.: python clips.py {orden} --cuenta mi_cuenta)")
        quitar = {"--cuenta", cuenta}
        return con_cuenta(cuenta, "render.py", [f"--{orden}", *[x for x in resto if x not in quitar]])
    if orden == "estado":
        return estado()
    if orden == "programar":
        return programar()
    if orden == "desprogramar":
        return desprogramar()
    print(__doc__)


if __name__ == "__main__":
    sys.exit(main() or 0)
