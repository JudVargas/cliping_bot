---
name: ui-layout-seguro
description: Reglas obligatorias y código de referencia para que nada se desborde ni se superponga (estructura de la app con menú lateral en cuadrícula, tarjetas fluidas, seguimiento de etapas StageTracker, fuentes sin caer a serif, container queries) y prueba automática de solapamientos. Úsalo siempre que construyas o corrijas la estructura general, tarjetas, listas, pasos o cualquier layout con texto dinámico.
---

# Layout seguro: nada se desborda, nada se superpone

## Problemas detectados en la app
En la pantalla de videos las cajas de etapas se salen de la tarjeta y se pisan con la vecina, el menú lateral queda encima del contenido y el texto aparece en fuente serif. Ver la sección de errores más abajo.

Causas típicas de desborde (buscarlas y eliminarlas):
1. Fila de etapas con `display:flex; flex-wrap:nowrap` y cajas con ancho fijo (`w-40`, `min-width: 150px`) o `white-space: nowrap`.
2. Hijos de flex/grid sin `min-width: 0` (por defecto no pueden encogerse por debajo de su contenido).
3. La tarjeta sin `min-width: 0`, sin `overflow: hidden` y dentro de una cuadrícula de columnas fijas.
4. Diseñar las etapas según el ancho de la **pantalla**, cuando el ancho real disponible es el de la **tarjeta**.
5. Descripción larga visible en todas las etapas al mismo tiempo.

## Reglas obligatorias
1. **Todo hijo de flex o grid que contenga texto lleva `min-width: 0`** (`min-w-0` en Tailwind).
2. **Nada de anchos fijos en píxeles para contenedores con texto.** Usar `minmax(0, 1fr)`, porcentajes, `max-width` o `clamp()`.
3. **Texto dinámico siempre con una política explícita:** `truncate` (una línea, con `title` para ver completo), `line-clamp-2` (hasta 2 líneas) o `overflow-wrap: anywhere` (puede partirse). Nunca dejar texto largo sin política.
4. **Elementos que no deben encogerse** (badges, iconos, botones) llevan `flex-shrink: 0`.
5. **Filas con varios elementos usan `flex-wrap`** o cambian a columna cuando falta espacio.
6. **Las tarjetas son contenedores de contenido:** `min-width: 0; overflow: hidden` (o `overflow: clip`) y `container-type: inline-size` para que sus partes se adapten a **su propio ancho** (container queries), no al de la pantalla.
7. **Cuadrícula de tarjetas fluida:** `grid-template-columns: repeat(auto-fill, minmax(min(100%, 20rem), 1fr)); gap: 16px;`. Nunca columnas fijas en px.
8. **Pruebas con datos extremos:** nombre de archivo de 80 caracteres sin espacios, 1 y 12 tarjetas, etapa con mensaje de error largo, ancho de 320 px.
9. Nunca ocultar un desborde con `overflow: hidden` como solución: primero resolver la causa. `overflow: hidden/clip` es el último seguro, no el arreglo.

## Código de referencia (usar tal cual, adaptando solo imports y campos)
Está en `.opencode/skill/ui-layout-seguro/referencia/`. **Copiar y reemplazar los componentes existentes; no dejar los viejos conviviendo con los nuevos.**

| Archivo | Para qué |
|---|---|
| `base.css` | reset, fuente con alternativas (nunca cae a serif), foco, `sr-only`, reduced-motion |
| `shell.css` + `Shell.tsx` | estructura de la app: menú lateral como **columna de la cuadrícula** (escritorio) y barra inferior (móvil) |
| `stages.ts` | `deriveStages(video)`: única fuente de verdad del estado de las etapas |
| `StageTracker.tsx` + `.css` | pasos en horizontal con una sola línea de detalle; vertical si la tarjeta es angosta (container query) |
| `StatusBadge.tsx`, `VideoCard.tsx`, `VideoGrid.css` | tarjeta de video y cuadrícula fluida |

## Errores que ya ocurrieron en este proyecto (no repetir)
1. **Menú lateral encima del contenido.** Causa: el menú es `position: fixed/absolute` (o mide más ancho) y el contenido reserva otro margen. Solución: el menú es una columna de `display: grid` (`232px minmax(0,1fr)`), con `position: sticky` si debe quedarse fijo. **Prohibido** `position: fixed` + `margin-left` para el layout principal.
2. **Fila de etapas que se sale de la tarjeta** (4 cajas con ancho propio y texto descriptivo en cada una). Solución: pasos de igual ancho `repeat(4, minmax(0, 1fr))`, etiqueta corta con elipsis y **una sola** línea de detalle (la de la etapa activa o con error) debajo.
3. **Texto en fuente serif (Times).** Causa: `font-family: var(--algo)` con una variable que no existe o que no se importó; el navegador descarta la declaración y usa la fuente por defecto. Solución: escribir siempre la pila completa de fuentes en `body` (ver `base.css`), importar `tokens.css` y `base.css` en `main.tsx` antes que cualquier otro CSS, importar los pesos de `@fontsource`, y ejecutar `node scripts/check-css-vars.mjs` (detecta `var(--x)` sin definir). Los botones e inputs necesitan `font: inherit`.
4. **Estados contradictorios** (badge "Listo" pero etapa "Momentos" en curso; video con error y todas las etapas en verde). Solución: todo sale de `deriveStages(video)`; el backend debe enviar `error_stage` cuando falla.
5. **Cajas anidadas innecesarias** ("Procesamiento" dentro de otro recuadro con borde). Una tarjeta = un solo nivel de borde; sin título "PROCESAMIENTO" en mayúsculas.

## Prueba automática de desbordes y solapamientos (Playwright)
Añadir a `e2e/layout.spec.ts` y ejecutarla con datos de prueba extremos (`VITE_MOCK=1`):
```ts
import { test, expect } from '@playwright/test'

const widths = [320, 360, 390, 768, 1024, 1440]

for (const w of widths) {
  test(`sin desbordes ni solapamientos a ${w}px`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: 900 })
    await page.goto('/?mock=extremos')
    await page.waitForSelector('.vcard')

    const problems = await page.evaluate(() => {
      const out: string[] = []
      const cards = [...document.querySelectorAll<HTMLElement>('.vcard')]
      // 1. Nada se sale de su tarjeta
      for (const card of cards) {
        const box = card.getBoundingClientRect()
        card.querySelectorAll<HTMLElement>('*').forEach((el) => {
          const r = el.getBoundingClientRect()
          if (r.width && (r.right > box.right + 1 || r.left < box.left - 1))
            out.push(`desborde: <${el.tagName.toLowerCase()} class="${el.className}">`)
        })
      }
      // 2. Las tarjetas no se pisan entre sí
      for (let i = 0; i < cards.length; i++) for (let j = i + 1; j < cards.length; j++) {
        const a = cards[i].getBoundingClientRect(), b = cards[j].getBoundingClientRect()
        const overlap = a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1
        if (overlap) out.push(`tarjetas ${i} y ${j} se superponen`)
      }
      // 3. El menú lateral no se superpone con el contenido
      const side = document.querySelector<HTMLElement>('.shell__side')
      const content = document.querySelector<HTMLElement>('.shell__content')
      if (side && content && getComputedStyle(side).display !== 'none') {
        const a = side.getBoundingClientRect(), b = content.getBoundingClientRect()
        if (a.right > b.left + 1) out.push('el menú lateral se superpone con el contenido')
      }
      // 4. Sin scroll horizontal de página
      if (document.documentElement.scrollWidth > document.documentElement.clientWidth)
        out.push('scroll horizontal en la página')
      return out
    })
    expect(problems, problems.join('\n')).toEqual([])
  })
}
```
El modo `?mock=extremos` debe incluir: un nombre de archivo de 80 caracteres sin espacios, 12 videos, una etapa con error de 200 caracteres y una tarjeta en cada estado.

## Procedimiento de corrección (cuando algo se ve mal)
1. Reproducir con el modo `extremos` a 320 px y a 1440 px y guardar capturas.
2. Identificar el elemento que se sale con el inspector (buscar el primero cuyo ancho supere al de su contenedor).
3. Aplicar las reglas 1-7 en orden; no usar `overflow: hidden` para esconder el problema.
4. Ejecutar `e2e/layout.spec.ts`; no cerrar la tarea mientras falle.
5. Revisar las capturas nuevas.
