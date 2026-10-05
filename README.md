# Clips automáticos — skill para Antigravity, Codex y Claude Code

Convierte vídeos largos en clips verticales con subtítulos animados y los **sube solos a TikTok y YouTube Shorts**,
con **varias cuentas** y un **estilo de edición distinto para cada una**. Todo en tu PC, gratis.

```
YouTube / tus vídeos ─► Whisper (transcribe) ─► IA elige los mejores momentos ─► 9:16 siguiendo caras
   ─► subtítulos palabra a palabra + gancho + logo + música ─► Chrome sube a su hora (y comprueba la cuenta)
```

## Instalar la skill

```bash
git clone https://github.com/davidrscout/clips-automaticos-skill
cd clips-automaticos-skill
```
- **Windows:** `powershell -ExecutionPolicy Bypass -File instalar_skill.ps1`
- **Mac / Linux:** `bash instalar_skill.sh`

Eso la copia a la carpeta de skills de cada herramienta:

| Herramienta | Carpeta | Cómo usarla |
|---|---|---|
| **Antigravity** | `~/.gemini/config/skills/` | Reinicia Antigravity y di "monta los clips automáticos" o `/clips-automaticos` |
| **Codex** (CLI, app o IDE) | `~/.agents/skills/` | Abre Codex y di "monta los clips automáticos" o `$clips-automaticos` |
| **Claude Code** (si está instalado) | `~/.claude/skills/` | `/clips-automaticos` |

Si prefieres que viva solo en un proyecto: copia `skills/clips-automaticos` a `<tu-proyecto>/.agents/skills/`
(lo leen Antigravity y Codex).

El agente te entrevista (cuentas, redes, horas, fuentes y **estilo de cada cuenta**), lo instala, te hace iniciar
sesión una vez, te enseña una previa de cada estilo para que la ajustes y deja las tareas programadas.

## Qué necesitas
- Python 3.10+ y Google Chrome. ffmpeg lo instala solo (Windows con winget, Mac con brew).
- Una IA para elegir momentos y escribir títulos:
  - con **Codex**: usa tu suscripción de ChatGPT con `codex exec`, sin clave de API;
  - con **Antigravity**: clave **gratis de Gemini** (https://aistudio.google.com/apikey);
  - también vale OpenRouter, OpenAI, un modelo local (LM Studio/Ollama) o `claude -p`.
- GPU NVIDIA opcional (Whisper va mucho más rápido).
- El PC encendido y con sesión iniciada a las horas de subida (Chrome se abre un minuto para subir).

## Personalización por cuenta (lo importante)
Cada cuenta tiene su bloque `estilo` en `config.yaml`: qué momentos elegir (instrucciones libres a la IA), duración,
encuadre, subtítulos (fuente, colores, mayúsculas, palabras por línea, salto, altura), gancho, logo, música,
velocidad, idioma de los títulos, hashtags y crédito. Presets listos (viral amarillo, Hormozi, pódcast limpio,
minimal, colores de marca) en [`references/personalizacion.md`](skills/clips-automaticos/references/personalizacion.md).

```
python clips.py previa --cuenta mi_cuenta    # renderiza 1 clip de prueba con el estilo actual
python clips.py rehacer --cuenta mi_cuenta   # aplica el estilo nuevo a los clips aún no subidos
```

## Uso manual (sin agente)
```bash
cp -r skills/clips-automaticos/plantilla ~/Clips && cd ~/Clips
python instalar.py                 # venv, dependencias, config.yaml y .env
# edita config.yaml y .env
venv/bin/python clips.py login     # (Windows: venv\Scripts\python clips.py login)
venv/bin/python clips.py procesar --cuenta mi_cuenta
venv/bin/python clips.py previa --cuenta mi_cuenta
venv/bin/python clips.py subir --cuenta mi_cuenta --red tiktok --ahora 1
venv/bin/python clips.py programar
```
`python clips.py` sin nada muestra todas las órdenes. Problemas típicos y arreglos:
[`references/problemas.md`](skills/clips-automaticos/references/problemas.md).

## Avisos
- Subir clips de otros creadores sin permiso puede traer reclamaciones de copyright o strikes. Lo seguro: vídeos
  propios, con permiso o con licencia Creative Commons BY (`busquedas_cc`; el crédito se pone solo). Tú decides.
- Empieza con pocos vídeos al día y ve subiendo.
- TikTok y YouTube cambian sus pantallas de vez en cuando: si una subida falla, la captura en `logs/` dice dónde
  y se ajusta `subir.py` (el agente lo sabe hacer con la skill).

Fuente de subtítulos incluida: Montserrat (SIL Open Font License, ver `plantilla/fuentes_tipo/OFL.txt`).
Detector de caras: OpenCV YuNet (`plantilla/modelos/`). Licencia del código: MIT.
