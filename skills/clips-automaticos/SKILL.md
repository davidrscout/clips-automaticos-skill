---
name: clips-automaticos
description: (Antigravity, Codex, Claude Code) Monta y mantiene un sistema LOCAL que convierte vídeos largos (canales de YouTube, búsquedas Creative Commons o vídeos propios) en clips verticales con subtítulos animados y los sube SOLO a TikTok y YouTube Shorts a sus horas, con varias cuentas y un estilo de edición PERSONALIZADO por cuenta. Usar cuando el usuario quiera "subir vídeos automáticos a redes", "clips automáticos", "un Opus Clip gratis", "automatizar TikTok/Shorts", "varias cuentas de clips", cambiar cómo se editan los vídeos de una cuenta (subtítulos, colores, gancho, logo, música, duración, qué momentos elegir) o arreglar subidas que fallan.
---

# Clips automáticos (TikTok + YouTube Shorts, multi-cuenta, estilo por cuenta)

Funciona igual en **Antigravity, Codex y Claude Code** (estándar Agent Skills). Los comandos se ejecutan en la
terminal del proyecto; necesitan red (pip, yt-dlp, subidas) y abrir Chrome, así que en Codex pide permiso o usa un
modo con acceso a red y fuera del sandbox de solo lectura cuando toque instalar, procesar o subir.

Sistema probado en producción: busca vídeos → los transcribe con Whisper → una IA elige los mejores momentos →
reencuadra a 9:16 siguiendo caras → quema subtítulos palabra a palabra → sube con Chrome (Playwright) a la hora de
cada público, comprobando ANTES que está en la cuenta correcta. Todo en local y gratis (salvo la IA si eliges una de pago).

El código completo está en `plantilla/` (junto a este fichero). **No lo reescribas: cópialo y configúralo.**
Lee `references/personalizacion.md` antes de tocar estilos y `references/problemas.md` cuando algo falle.

## Regla de oro: cada cuenta tiene SU estilo

Un mismo estilo para todas las cuentas no funciona (un pódcast serio no se edita como un vídeo de MrBeast). Por eso
el paso 3 (entrevista de estilo) y el paso 6 (bucle de previa) **no se saltan nunca**, aunque el usuario tenga prisa.

## Flujo para montarlo de cero

### 1. Requisitos (compruébalos tú, no preguntes)
- Python 3.10+, Google Chrome instalado, ~5 GB libres. GPU NVIDIA opcional (Whisper va más rápido).
- Windows, Mac o Linux. Las subidas abren Chrome VISIBLE (TikTok bloquea el modo oculto): el PC debe estar encendido
  y con la sesión de usuario iniciada a las horas de subida.

### 2. Copiar la plantilla
Copia la carpeta `plantilla/` entera a donde el usuario quiera el proyecto (por defecto `~/Clips`) y ejecuta allí
`python instalar.py` (crea `venv/`, instala dependencias y ffmpeg, crea `config.yaml` y `.env`).
A partir de aquí usa SIEMPRE el python del venv: `venv\Scripts\python` (Windows) o `venv/bin/python` (Mac/Linux).

### 3. Entrevista (una pregunta cada vez o en bloque corto; no inventes respuestas)
Por **cada cuenta**:
1. Nombre interno (ej. `humor_en`) y de qué va el contenido.
2. Redes: TikTok (@usuario), YouTube (ID del canal `UC...`: en YouTube Studio → Configuración → Canal → Configuración
   avanzada, o en la URL de studio.youtube.com/channel/UC...). Cuántos vídeos/día por red.
3. Público: idioma y país → `idioma` y `zona_horaria`; horas de subida (si no sabe: 3 franjas, 9:00 / 14:00 / 20:00 de su público).
4. Fuentes: canales de YouTube, búsquedas Creative Commons, o carpeta con vídeos propios.
5. **Estilo** (ofrece los presets de `references/personalizacion.md` y que elija o mezcle):
   subtítulos (mayúsculas, colores, palabras por línea, fuente), gancho arriba sí/no, logo, música, velocidad,
   duración de los clips, y en texto libre QUÉ momentos quiere y cómo deben ser los títulos (→ `estilo.editor`).
6. Qué perfil de Chrome usa cada red. Varias cuentas pueden compartir perfil si son del mismo login; si TikTok/Google
   tienen logins distintos, perfiles distintos (A, B, C...).

Global (una vez): qué IA usar como "cerebro" y si quiere avisos por Telegram. Recomendación según su herramienta:
- **Codex** (suscripción de ChatGPT): `tipo: comando` con `codex exec ... -` → sin clave de API. Pruébalo antes con
  `echo 'Devuelve SOLO {"ok": true}' | codex exec --skip-git-repo-check --ephemeral -s read-only -`; si da error de
  modelo, añade `-m <modelo válido>` al comando.
- **Antigravity**: Gemini por API con clave gratis de https://aistudio.google.com/apikey (`tipo: api`, ya por defecto).
- **Claude Code**: `tipo: comando` con `claude -p --output-format text`.
- Cualquiera: OpenRouter/OpenAI/modelo local por `tipo: api`.

### 4. Escribir `config.yaml` y `.env`
- Parte de `config.ejemplo.yaml` (ya copiado como `config.yaml`): borra las cuentas de ejemplo y crea las suyas.
- Las claves van SOLO en `.env` (nunca en `config.yaml`).
- Valida el YAML: `venv/bin/python -c "import yaml;yaml.safe_load(open('config.yaml',encoding='utf-8'))"`.

### 5. Login (lo hace el usuario, una vez)
`python clips.py login` abre un Chrome por perfil; el usuario inicia sesión en Google/YouTube y TikTok y CIERRA las
ventanas. Luego se ejecuta solo `comprobar`: cada red debe decir `OK`. Si dice CUENTA EQUIVOCADA, corrige `usuario`/
`canal`/`perfil` en config (nunca desactives la comprobación).

### 6. Primer procesado + bucle de previa (personalización)
1. `python clips.py procesar --cuenta <cuenta>` (la primera vez descarga el modelo de Whisper; puede tardar).
2. `python clips.py previa --cuenta <cuenta>` → `previas/<cuenta>.mp4` + `<cuenta>_1..3.jpg`.
3. **Mira tú los 3 .jpg** (lee las imágenes) y comprueba: subtítulos legibles y sin tapar caras, gancho dentro de
   pantalla, logo donde toca. Enséñale al usuario el .mp4 y pregúntale qué cambiar.
4. Ajusta `estilo` de esa cuenta en `config.yaml` y repite la previa (`--clip N` para ver otro clip) hasta que diga que sí.
5. `python clips.py rehacer --cuenta <cuenta>` re-renderiza con el estilo final los clips que aún no se han subido.
   Si cambió `estilo.editor`, `corte` o duraciones, hay que volver a CORTAR: borra `cuentas/<cuenta>/trabajo/*.clips.json`
   y los `listos/` no subidos, y vuelve a `procesar`.

### 7. Prueba de subida y automatización
- `python clips.py subir --cuenta <cuenta> --red tiktok --ahora 1` y lo mismo con `youtube`. Verifica en la app que
  el vídeo está publicado y en la cuenta correcta.
- `python clips.py programar` → procesar cada 4 h y subir cada 30 min (respeta `horas` y `por_dia`).
- `python clips.py estado` para ver cola y subidos hoy. Logs y capturas de error en `logs/`.

## Cambios habituales después
- "Que los subtítulos de X sean…" / "quita el gancho" / "pon mi logo" → editar `cuentas.<x>.estilo`, `previa`, `rehacer`.
- "Que elija otro tipo de momentos" → `estilo.editor` (texto libre que la IA obedece) y volver a cortar.
- "Más / menos vídeos" → `redes.<red>.por_dia` y `horas` (una hora por vídeo).
- "Añade una cuenta" → nuevo bloque en `cuentas:` (pasos 3-7 solo para ella).
- "Pausa una cuenta" → `activo: false`.

## Avisos que hay que dar al usuario (una vez, sin sermones)
- Subir clips de creadores ajenos sin permiso puede traer reclamaciones de copyright o strikes. Lo seguro: vídeos
  propios, con permiso, o Creative Commons BY (`busquedas_cc`, el crédito se pone solo). Es decisión suya.
- Empezar con pocos vídeos/día y subir poco a poco reduce el riesgo de que TikTok limite la cuenta.
- TikTok y YouTube cambian sus pantallas: si una subida falla, la captura en `logs/` dice dónde y se ajustan los
  selectores de `subir.py` (ver `references/problemas.md`).

## Mapa del código (plantilla/)
| Fichero | Qué hace |
|---|---|
| `clips.py` | Punto de entrada único (procesar, subir, login, comprobar, previa, rehacer, estado, programar) |
| `config.ejemplo.yaml` | Configuración comentada con 2 cuentas de ejemplo con estilos distintos |
| `buscar.py` → `descargar.py` | Fuentes nuevas solo cuando falta reserva (yt-dlp) |
| `transcribir.py` | Whisper local con tiempos por palabra; descarta audio en otro idioma |
| `cortar.py` | La IA elige momentos (o trocea en partes) y escribe título, gancho, descripción y hashtags |
| `reencuadre.py` | 9:16 siguiendo caras (OpenCV YuNet), apila 2 personas o difumina |
| `render.py` | Subtítulos ASS animados, gancho, logo, música, velocidad, previa |
| `subir.py` | Playwright con el Chrome real del usuario; verifica cuenta; cupo diario y franjas |
| `comun.py` | Config multi-cuenta, IA (API compatible OpenAI o CLI), candados, logs |
