# Prompt de reparación del frontend (escritorio y móvil)

## Antes de pegarlo
1. Descomprime el zip en la raíz del proyecto (sobrescribe `.opencode/skill/ui-layout-seguro/`). Se agrega la carpeta `scripts/` y `demo/`.
2. Abre `demo/demo.html` en el navegador: así se ve el resultado esperado (funciona sin instalar nada).
3. Sesión **nueva** de opencode, modo **Plan** (Tab) y pega el prompt. Cuando el plan sea correcto, pasa a **Build**.
4. Si el modelo acepta imágenes, adjunta tu captura; si no, el prompt ya describe el problema.

## Prompt
```
Lee el skill ui-layout-seguro y TODOS los archivos de su carpeta "referencia/".
Esos archivos son la implementación correcta: úsalos como base, adaptando solo
imports, rutas y nombres de campos a mi proyecto. No los reinterpretes.

PROBLEMAS ACTUALES (en escritorio, a 1440 px)
1. El menú lateral queda ENCIMA del contenido: el logo "ClipForge" y los items
   de navegación quedan tapados por la tarjeta de "Subir video".
2. En cada tarjeta de video, las cajas de etapas (Subida, Transcripción,
   Momentos, Listo) siguen en una fila con ancho propio, se salen de la
   tarjeta y quedan cortadas; el texto de una pisa a la siguiente.
3. La fuente se ve en serif (tipo Times) en toda la app. Debe ser IBM Plex Sans.
   Sospecha: variable CSS de fuente sin definir, o @fontsource sin importar.
4. Los estados se contradicen: el video con error muestra todas las etapas en
   verde; el video "Listo" muestra "Buscando los mejores momentos".
5. Hay un recuadro "PROCESAMIENTO" (mayúsculas con barra) dentro de otro
   recuadro: demasiado anidado.

PASOS (en este orden, esperando mi OK después del plan)
1. Base y fuentes: importa en main.tsx, en este orden, tokens.css y base.css
   (de referencia/base.css) y los pesos de @fontsource/ibm-plex-sans (400, 500,
   600) y @fontsource/ibm-plex-mono (400). Ejecuta
   `node scripts/check-css-vars.mjs` y corrige TODA variable CSS sin definir.
   Confirma que el texto ya no sale en serif.
2. Estructura de la app: reemplaza el layout actual por Shell.tsx + shell.css.
   El menú lateral debe ser una columna de la cuadrícula (232px | resto), nunca
   position:fixed/absolute con margen. En pantallas < 1024px, barra inferior.
3. Etapas: reemplaza el componente actual por stages.ts + StageTracker.tsx +
   StageTracker.css. Pasos en horizontal de igual ancho, con una sola línea de
   detalle debajo; vertical si la tarjeta es angosta. Elimina los componentes y
   estilos viejos que queden sin uso.
4. Estado: todo sale de deriveStages(video). Si el backend no envía el campo
   error_stage cuando una etapa falla, agrégalo (modelo Video, guardado al
   fallar cada etapa, respuesta de la API y tipo en el frontend).
5. Tarjeta y cuadrícula: reemplaza por StatusBadge.tsx, VideoCard.tsx y
   VideoGrid.css (un solo nivel de borde, título con line-clamp, badge con
   flex-shrink:0, botón de eliminar de 44px en pantallas táctiles).
6. Pruebas: crea el modo ?mock=extremos (nombre de 80 caracteres sin espacios,
   12 videos, un error largo, un video en cada estado) y el test
   e2e/layout.spec.ts de ui-layout-seguro. Ejecútalo a 320, 360, 390, 768,
   1024 y 1440 px. No termines hasta que pase.
7. Genera capturas a esos tamaños, revísalas y compáralas con demo/demo.html.

REGLAS
- Primero el plan (archivos a modificar y borrar); espera mi OK.
- No cambies la lógica del backend salvo el campo error_stage.
- No uses overflow:hidden para esconder desbordes: corrige la causa.
- Un solo color de acento, sin brillos ni degradados decorativos.
- Al final: resumen corto, resultado de los tests y de check-css-vars.
```

## Si algo sigue mal después
Pega este mensaje corto al modelo, con la captura o el texto del problema:
```
Sigue mal: [describe qué ves y a qué ancho]. Abre la implementación de
referencia correspondiente en ui-layout-seguro/referencia, compárala con mi
código archivo por archivo y dime las diferencias antes de cambiar nada.
```
