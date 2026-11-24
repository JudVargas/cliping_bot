# Prompt de corrección y rediseño del frontend

## Antes de pegarlo
1. Descomprime el zip en la raíz del proyecto (sobrescribe los skills anteriores con el mismo nombre).
2. Borra la carpeta `.opencode/skill/ui-futurista/` (el prompt también se lo pide al agente).
3. Abre una **sesión nueva** en opencode, cambia a modo **Plan** (Tab) y pega el prompt.
4. Cuando el plan te convenza, pasa a modo **Build**.
5. Si el modelo acepta imágenes, adjunta la captura del error; si no, el prompt ya describe el problema.

## Prompt
```
Usa los skills ui-layout-seguro, ui-sistema-diseno, ui-responsive y
ui-componentes-clipforge. Si existe la carpeta .opencode/skill/ui-futurista,
elimínala: queda reemplazada por ui-sistema-diseno.

PROBLEMA 1 (bug de layout)
En la pantalla de videos, cada tarjeta tiene una sección "Procesamiento" con
4 cajas de etapas (Subida, Transcripción, Momentos, Listo) en una fila.
Esa fila no cabe en la tarjeta: las cajas se salen, el texto de una etapa se
superpone con el de otra y la tarjeta se mezcla con la de al lado. Pasa al
cargar un video. Causas probables: fila sin wrap con anchos fijos, hijos de
flex/grid sin min-width:0, tarjeta sin container ni overflow controlado,
cuadrícula con columnas fijas.

PROBLEMA 2 (diseño)
No me gustan la fuente ni los colores actuales (demasiado neón: violeta, cian,
verde fosforescente, brillos). Quiero un diseño profesional, sobrio y moderno,
con un único color de acento, que funcione bien en celular y en computador.

QUÉ HACER
1. Diagnóstico: localiza los componentes de la tarjeta de video y de las
   etapas, y explícame en 5 líneas la causa exacta del desborde.
2. Reescribe el seguimiento de etapas como StageTracker siguiendo ui-layout-seguro:
   - lista vertical en tarjetas angostas y 4 columnas en tarjetas anchas, usando
     container queries (no breakpoints de pantalla);
   - solo la etapa activa muestra su detalle (máximo 2 líneas);
   - estados pendiente / en curso / listo / error derivados de una única
     función deriveStages(video), para que el badge y las etapas no se
     contradigan.
3. Corrige la tarjeta de video y su cuadrícula: grid auto-fill con
   minmax(min(100%, 20rem), 1fr), min-width:0, título con line-clamp y badge
   con flex-shrink:0.
4. Aplica el nuevo sistema de diseño de ui-sistema-diseno: tokens en
   tokens.css, fuentes IBM Plex Sans e IBM Plex Mono (con @fontsource),
   paleta grafito + cobalto, tema oscuro y claro, sin brillos ni degradados
   decorativos, y sin títulos en mayúsculas con barra lateral. Reemplaza todos
   los colores y fuentes antiguos en TODO el frontend, no solo en esta pantalla.
5. Añade el modo de datos de prueba ?mock=extremos y el test
   e2e/layout.spec.ts de ui-layout-seguro. Ejecútalo a 320, 360, 390, 768,
   1024 y 1440 px y corrige hasta que pase.
6. Genera capturas a esos tamaños, revísalas y pasa la lista de ui-calidad.

REGLAS
- Primero muéstrame el plan (archivos a tocar) y espera mi OK.
- No cambies la lógica del backend ni la API.
- No uses overflow:hidden para esconder el desborde: corrige la causa.
- Al terminar: resumen corto de cambios, resultado de los tests y capturas.
```

## Si el resultado no te convence del todo
Pide ajustes concretos, de a uno por vez:
- "Haz las tarjetas más compactas en móvil (menos padding y una sola línea de meta)."
- "Sube el contraste del texto secundario en el tema oscuro."
- "Prueba el acento en teal (#14B8A6) en lugar de cobalto y compara capturas."
- "Muestra el nombre del archivo en una sola línea con elipsis y el nombre completo en un tooltip."
