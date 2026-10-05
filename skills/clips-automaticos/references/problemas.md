# Problemas conocidos y cómo se arreglan

Primero: `logs/clips.log` y las capturas `logs/*_error_*.png` / `*_cuenta_*.png` (dicen en qué pantalla se quedó).

## Subida
| Síntoma | Causa | Arreglo |
|---|---|---|
| `SIN SESIÓN` | La sesión caducó o nunca se inició en ese perfil | `python clips.py login`, iniciar sesión, cerrar ventanas |
| `CUENTA EQUIVOCADA` | En ese perfil hay otra cuenta, o `usuario`/`canal` mal escritos | Corregir `perfil`, `usuario` (sin @) o `canal` (UC...). Nunca quitar la comprobación |
| Google dice "este navegador no es seguro" al iniciar sesión | Se intentó loguear desde Playwright | El login se hace SIEMPRE con `clips.py login` (Chrome normal, sin automatizar) |
| Chrome no abre / se cierra solo | Hay otra ventana de Chrome usando ESE perfil | Cerrar las ventanas de `perfiles/X`; el script reintenta 3 veces |
| Chrome 136+ no deja usar el perfil principal | Política nueva de Chrome | Por eso se usan perfiles propios en `perfiles/`; no apuntar a tu perfil personal |
| Subida a medias / se queda en el editor | TikTok o YouTube cambiaron la pantalla | Mirar la captura y ajustar selectores en `subir.py` (`subir_tiktok` / `subir_youtube`) |
| TikTok saca un modal de "revisiones automáticas" | Aviso nuevo | `cerrar_avisos_tiktok` pulsa Activar/Entendido; si el texto cambia, añadirlo a la lista |
| TikTok muestra el vídeo como "Solo yo" un rato | TikTok lo está revisando | Normal; pasa a público solo |
| Vídeo duplicado | Dos subidas a la vez | Ya hay candado; no lanzar `subir` a mano mientras corre la tarea |
| YouTube: campos de título no se encuentran | Cambió el DOM | Hoy son `#title-textarea #textbox` y `#description-textarea #textbox` |
| Modo oculto (`--oculto`) falla en TikTok | TikTok bloquea headless | Subir siempre con ventana visible |

## Procesado
| Síntoma | Causa | Arreglo |
|---|---|---|
| `ffmpeg no encontrado` | Recién instalado y la terminal no lo ve | Cerrar y abrir la terminal |
| El proceso se cuelga en ffmpeg | Salida de error enorme en una tubería | Ya se captura en memoria con `run()`; no usar `stderr=PIPE` sin leerlo |
| Whisper en CPU muy lento | Sin GPU NVIDIA | `whisper_modelo: "small"` o `"medium"` |
| Error de DLL de CUDA en Windows | Faltan cuBLAS/cuDNN | `instalar.py` los instala; si no, `whisper_dispositivo: "cpu"` |
| `av.open() got an unexpected keyword argument 'metadata_errors'` | PyAV 15+ con faster-whisper 1.2 | Ya parcheado en `transcribir.py` |
| yt-dlp: "Sign in to confirm you're not a bot" / sin formatos | YouTube exige motor JS o bloquea la IP | `pip install -U yt-dlp deno` en el venv; si persiste, esperar o cambiar de red |
| "la IA no devolvió momentos válidos" | Clave mal, cuota agotada o respuesta sin JSON | Probar la clave; cambiar de `modelo`; mirar el error en el log (`cerebro falló`) |
| Todos los vídeos "descartados por idioma" | `idioma` de la cuenta no coincide con el audio | Poner el idioma correcto o `"auto"` |
| Subtítulos con fuente rara | La fuente no está instalada ni en `fuentes_tipo/` | Copiar el `.ttf` a `fuentes_tipo/` y usar su nombre interno exacto |
| Música no suena | La carpeta no existe o no tiene audio compatible | `.mp3/.wav/.m4a/.ogg/.aac/.flac` dentro de `musica.carpeta` |

## Tareas programadas
- Windows: `Clips-Procesar` y `Clips-Subir` en el Programador de tareas (usan `pythonw`, sin ventanas). El usuario
  debe tener la sesión iniciada para que Chrome se vea.
- Mac/Linux: líneas marcadas `# clips-auto` en `crontab -l`. En Linux sin escritorio no hay Chrome visible: usar un
  escritorio real o `xvfb-run` (TikTok puede bloquearlo).
- Quitar todo: `python clips.py desprogramar`.
