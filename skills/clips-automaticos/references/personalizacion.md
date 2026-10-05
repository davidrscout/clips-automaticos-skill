# Personalización por cuenta

Todo vive en `config.yaml`. El bloque `estilo:` de arriba del todo es el estilo por defecto; cada cuenta pone en
`cuentas.<cuenta>.estilo` SOLO lo que cambia (se mezcla campo a campo). Tras cambiar algo:

```
python clips.py previa --cuenta <cuenta>      # 1 clip de prueba en previas/ (+ 3 fotogramas)
python clips.py rehacer --cuenta <cuenta>     # aplica el estilo a todos los clips aún no subidos
```

## Todas las opciones

| Opción | Valores | Qué cambia | ¿Hay que volver a cortar? |
|---|---|---|---|
| `editor` | texto libre | Instrucciones a la IA: qué momentos buscar, qué evitar, tono de títulos, emojis, idioma | Sí |
| `corte` | `momentos` / `secuencial` | La IA elige lo mejor / trocea el vídeo entero en Parte 1, 2, 3… | Sí |
| `clip_min_seg`, `clip_max_seg` | segundos | Duración de cada clip | Sí |
| `clips_por_video_max` | número | Cuántos clips como mucho de cada vídeo | Sí |
| `encuadre` | `auto` / `seguir` / `blur` / `crop` | auto: sigue la cara, apila 2 personas o difumina; seguir: siempre sigue a la cara principal; blur: vídeo entero sobre fondo difuminado; crop: recorte central | No |
| `velocidad` | 1.0 – 1.15 | Acelera vídeo y voz (1.05-1.1 suele subir la retención) | No |
| `calidad_crf` | 18 – 23 | Calidad/peso del vídeo | No |
| `subtitulos.activo` | true/false | Subtítulos sí/no | No |
| `subtitulos.fuente` | nombre de fuente | Tipografía. Mete el `.ttf` en `fuentes_tipo/` y pon su nombre interno (ej. "Montserrat ExtraBold") | No |
| `subtitulos.tamano` | 50 – 110 | Tamaño de letra (lienzo de 1080×1920) | No |
| `subtitulos.color` / `color_activo` | `#RRGGBB` | Color del texto / de la palabra que suena | No |
| `subtitulos.contorno`, `color_contorno`, `sombra` | px / `#RRGGBB` | Borde y sombra | No |
| `subtitulos.mayusculas` | true/false | TODO EN MAYÚSCULAS o normal | No |
| `subtitulos.palabras_por_linea` | 1 – 6 | 1-2 = ritmo "Hormozi"; 4-6 = más calmado | No |
| `subtitulos.salto` | 100 – 130 | % de tamaño de la palabra activa (100 = sin salto) | No |
| `subtitulos.altura` | px o null | Distancia desde abajo (null = automático según encuadre) | No |
| `gancho.activo` | true/false | Texto fijo arriba con fondo (lo escribe la IA) | No |
| `gancho.segundos` | 0 o N | 0 = todo el clip; 3 = solo al principio | No |
| `gancho.tamano`, `color_texto`, `color_fondo`, `altura`, `mayusculas` | | Aspecto y posición del gancho | No |
| `logo.fichero` | ruta a PNG (con transparencia) | Marca de agua. Vacío = sin logo | No |
| `logo.posicion` | `arriba-derecha`, `arriba-izquierda`, `arriba-centro`, `abajo-derecha`, `abajo-izquierda`, `abajo-centro` | Dónde va | No |
| `logo.ancho`, `opacidad`, `margen` | px / 0-1 / px | Tamaño, transparencia y separación del borde | No |
| `musica.carpeta` | carpeta con .mp3/.wav | Música de fondo aleatoria en bucle. Vacío = sin música | No |
| `musica.volumen` | 0.05 – 0.2 | Volumen de la música respecto a la voz | No |
| `textos.idioma` | `es`, `en`… o null | Idioma de títulos/descripciones (puede ser distinto del audio) | Sí (los títulos se escriben al cortar) |
| `textos.hashtags_base` | lista | Hashtags que van siempre | Sí |
| `textos.max_hashtags` | número | Máximo de hashtags | Sí |
| `textos.credito`, `plantilla_credito` | true/false, texto con `{canal}` y `{url}` | Crédito al autor original en la descripción (con CC BY va siempre) | No |

Fuera de `estilo`, por cuenta: `idioma` (del audio), `zona_horaria`, `redes.<red>.{por_dia, horas, perfil, usuario, canal}`,
`fuentes.*`, e incluso `cerebro` (una cuenta puede usar otra IA).

"Volver a cortar" = borrar `cuentas/<cuenta>/trabajo/*.clips.json` y los clips de `listos/` que aún no se han subido,
y ejecutar `python clips.py procesar --cuenta <cuenta>`.

## Presets (copiar dentro de `cuentas.<cuenta>.estilo`)

### Viral amarillo (tipo Submagic) — el que viene por defecto
```yaml
estilo:
  subtitulos: {mayusculas: true, color: "#FFFFFF", color_activo: "#FFE500", palabras_por_linea: 3, salto: 110}
  gancho: {activo: true}
```

### Hormozi (palabras gordas de 1-2 en 1-2, verde)
```yaml
estilo:
  velocidad: 1.08
  subtitulos: {tamano: 100, palabras_por_linea: 2, color_activo: "#3CFF4E", salto: 120, contorno: 8}
  gancho: {activo: true, segundos: 3}
```

### Limpio / pódcast serio
```yaml
estilo:
  clip_min_seg: 30
  clip_max_seg: 75
  subtitulos: {mayusculas: false, tamano: 64, color_activo: "#FFFFFF", salto: 100, palabras_por_linea: 5, contorno: 4}
  gancho: {activo: false}
  logo: {fichero: "logos/mi_logo.png", posicion: "arriba-derecha", ancho: 150, opacidad: 0.8}
```

### Minimal sin texto (solo vídeo + música, para contenido visual)
```yaml
estilo:
  encuadre: "blur"
  subtitulos: {activo: false}
  gancho: {activo: true, segundos: 3}
  musica: {carpeta: "musica", volumen: 0.15}
```

### Marca con colores propios (ej. rosa y negro)
```yaml
estilo:
  subtitulos: {color: "#FFFFFF", color_activo: "#FF3EA5", color_contorno: "#000000"}
  gancho: {color_texto: "#000000", color_fondo: "#FF3EA5"}
```

## Ejemplos de `editor` (lo que más cambia el resultado)

```yaml
editor: |
  Busca momentos graciosos o de tensión, con remate claro al final. Evita política y temas sensibles.
  Títulos cortos en minúscula, un emoji al final como mucho.
```
```yaml
editor: |
  Es un canal de finanzas personales. Elige consejos concretos con una cifra o un "error que comete todo el mundo".
  Nada de recomendaciones de inversión concretas. Títulos en español de España, sin emojis, en forma de pregunta.
```
```yaml
editor: |
  Clips de entrevistas a deportistas. Prioriza anécdotas personales y declaraciones polémicas.
  El gancho debe ser una cita literal corta de lo que dice la persona.
```

## Comprobación visual (para el agente)
En cada previa mira los 3 fotogramas `previas/<cuenta>_1..3.jpg`:
- los subtítulos no tapan la boca/cara ni se salen de pantalla (si no: `subtitulos.altura` o `tamano`);
- el gancho cabe en 1-2 líneas (si no: `gancho.tamano` más pequeño o pedir en `editor` ganchos más cortos);
- el logo no choca con el gancho (si choca: `logo.posicion` abajo, o `gancho.altura` más baja);
- en encuadre `dividir` (2 personas) los subtítulos quedan en la junta del medio.
