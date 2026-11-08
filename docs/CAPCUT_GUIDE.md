# Guía CapCut — video demo AGENT RUSH (nivel: cero experiencia)

Objetivo: un video de ~90 s con voz en off en inglés, sin editar nada complicado.
**Solo vas a hacer 4 cosas:** nuevo proyecto → soltar el video → soltar el audio → exportar.

> **Buena noticia:** CapCut **sí genera la voz** (Text to speech). Podés hacer todo
> dentro de CapCut, sin ElevenLabs. Ver **Opción A** abajo.

---

## Elegí cómo generás la voz

- **Opción A — CapCut (más fácil, todo en una app):** ver la sección
  “Voz con CapCut” más abajo. No necesitás descargar nada.
- **Opción B — ElevenLabs (voz más natural):** seguí “Antes de abrir CapCut”.

---

## Voz con CapCut (Opción A)

1. **Create project** → **Import** → `agent_rush_demo_cut.mp4` → arrastralo a la línea de tiempo.
2. Arriba: **Text → Add text**.
3. **Pegá el guion** de `docs/narration_en.txt`.
4. Con el texto seleccionado, buscá **Text to speech** (ícono 🔊 / “Read text”).
5. Elegí una voz **English** (*Brian*, *Adam* o “Narrator”) → **Generate**.
6. CapCut crea una **pista de audio** con la voz.
7. Si **no querés ver el texto**: borrá el clip de texto (solo el texto, no el audio)
   o bajá su opacidad. Si lo querés como subtítulo, dejalo.
8. Ajustes: arrastrá el texto para retrasar la voz ~0.5 s; clic en el texto →
   **Speed** para cambiar el ritmo.
9. **Export** → MP4, 1080p, 30 fps.

> El guion tiene ~185 palabras (~1.100 caracteres). Si CapCut corta el texto por
> bloque, partilo en 2–3 bloques; los reproduce en orden.
> No le pongas música encima: tapa la voz.

---

## Antes de abrir CapCut (Opción B): prepara 2 archivos

1. **El video (ya está listo, no lo toques):**
   ```
   C:\Users\josem\projects\Agent the Rush\my-agent-system\docs\playwright_spectator\agent_rush_demo_cut.mp4
   ```

2. **La voz en off (MP3 de ElevenLabs):**
   - Entrá a https://elevenlabs.io → logueate.
   - **Text to Speech**.
   - Elegí una voz en **US English** (por ejemplo *Brian* o *Adam*), tono tranquilo.
   - Pegá el guion de `docs/narration_en.txt`.
   - **Generate** → **Download** el MP3.
   - Guardalo, por ejemplo, en el Escritorio como `narracion.mp3`.

> Tip: escuchá el MP3 una vez. Si se siente lento o rápido, en ElevenLabs cambia el *Speed* a 0.95–1.05 y volvé a generar. Nada más.

---

## En CapCut (versión de escritorio, Windows)

### 1) Crear el proyecto
- Abrí **CapCut** (si te pide cuenta, logueate con Google).
- Botón **Create project** (o **New project**).

### 2) Meter el video
- Arriba/izquierda, botón **Import** (o **Media** y el **+**).
- Elegí `agent_rush_demo_cut.mp4`.
- **Arrastralo** desde la bandeja hacia la **línea de tiempo** (la franja de abajo).

### 3) (Opcional pero recomendado) Poner el formato 16:9
- Menú de arriba **Ratio** (o **Aspect ratio** / el ícono de proporción).
- Elegí **16:9**. El video ya es 16:9, así que solo se vea bien.

### 4) Meter la voz en off
- Arriba, botón **Audio**.
- **Import** (o **Upload**) → elegí `narracion.mp3`.
- **Arrastrá el audio** a la línea de tiempo, **debajo** del video (en una pista abajo).

### 5) Que arranque cuando querés
- El audio empieza apenas lo soltás. Si querés que la voz entre ~0.5 s después:
  - Hacé clic en el clip de audio (se pone celeste).
  - **Arrastralo a la derecha** un poquito (~0.5 s).
- Si el audio queda **más largo** que el video (no debería), recortá el audio:
  - Clic en el audio, y en el menú **Split** para cortar, o arrastrá el **borde derecho** del audio hacia la izquierda.

### 6) (Opcional) Título de 3 segundos
- Arriba, botón **Text** → **Add text** (o **Default text**).
- Escribí: `AGENT RUSH — Rush Protocol`.
- Estiralo sobre los primeros **3 segundos** del video (arrastrá su borde derecho a la izquierda).
- Agrandá la letra y arrastrá el texto arriba-centro. Listo.

### 7) (Opcional) Subtítulos automáticos en inglés
- Arriba, botón **Captions** (o **Text → Auto captions**).
- Idioma: **English**. **Generar**.
- CapCut los ubica solo. Si no los querés, salteá este paso.

### 8) Revisar
- Dale **Play** con el volumen. Mirá una vez completa.
- ¿La voz se escucha bien? ¿termina antes del final? Bien.

### 9) Exportar
- Arriba a la derecha, botón **Export**.
- Opciones: **Format MP4**, **Resolution 1080p**, **Frame rate 30**.
- Nombre: `agent_rush_demo_final`.
- **Export** → esperá (1–3 min).

---

## Subir el video y cerrar la entrega

1. Subilo a **YouTube** (poné **Unlisted**) o a **Loom**.
2. Copiá el **link**.
3. Pegalo en `SUBMISSION.md`, en la línea que dice:
   ```
   - **Video:** `<PENDING ...>`
   ```
   Reemplazá todo entre `< >` por tu URL.
4. (Si podés) avisame la URL y lo dejo también en el README y en el deck.

---

## Atajos mentales

- **Línea de tiempo** = la pista de abajo donde viven los clips.
- **Arrastrar** = clic sostenido y mover.
- **Recortar** = arrastrar el borde del clip o **Split** en el punto.
- **Pista de audio** = una fila debajo del video.
- Si algo sale mal: **Ctrl + Z** deshace. Nada se rompe.

## Si te trabás
- No te compliques: **no hace falta** agregar música ni transiciones. Con video + voz + (opcional título) ya queda profesional.
- Si CapCut te pelea, mandame el MP3 de ElevenLabs y te lo mezclo yo con ffmpeg y te devuelvo el MP4 final listo.
