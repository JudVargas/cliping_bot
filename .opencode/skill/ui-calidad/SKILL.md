---
name: ui-calidad
description: Lista de verificación de calidad del frontend (accesibilidad, rendimiento móvil, estados, contraste) y procedimiento para revisar capturas a 5 tamaños con Playwright. Úsalo al terminar una pantalla o antes de hacer commit de una etapa del frontend.
---

# Calidad del frontend: revisar antes de dar por terminado

## 1. Verificación visual con Playwright
Instalar una vez: `npm i -D @playwright/test && npx playwright install chromium`.

```ts
// frontend/e2e/screens.spec.ts
import { test } from '@playwright/test'

const sizes = [
  { name: 'movil-360',  width: 360,  height: 740 },
  { name: 'movil-390',  width: 390,  height: 844 },
  { name: 'tablet-768', width: 768,  height: 1024 },
  { name: 'laptop-1024', width: 1024, height: 768 },
  { name: 'desktop-1440', width: 1440, height: 900 },
]
const routes = ['/', '/videos/demo', '/clips/demo', '/ajustes']

for (const s of sizes) for (const r of routes) {
  test(`${s.name} ${r}`, async ({ page }) => {
    await page.setViewportSize({ width: s.width, height: s.height })
    await page.goto(`http://localhost:5173${r}`)
    await page.waitForLoadState('networkidle')
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth)
    if (overflow) throw new Error(`Scroll horizontal en ${s.name} ${r}`)
    await page.screenshot({ path: `e2e/shots/${s.name}${r.replace(/\//g, '_')}.png`, fullPage: true })
  })
}
```
Después de generar las capturas: abrirlas, compararlas y corregir lo que se vea cortado, apretado, desalineado o con poco contraste. Para que funcione sin backend, las rutas `demo` deben usar datos simulados (mock) cuando la variable `VITE_MOCK=1`.

## 2. Accesibilidad
- [ ] Foco visible en todo elemento interactivo (`:focus-visible` con anillo `ion` de 2 px y separación de 2 px).
- [ ] Orden de tabulación lógico; sin trampas de foco, salvo en modales y hojas (donde es intencional).
- [ ] Cada botón con solo icono tiene `aria-label` en español.
- [ ] Contraste del texto ≥ 4.5:1 (≥ 3:1 en texto grande y en bordes de componentes).
- [ ] El color nunca es la única señal (estado = color + icono o texto).
- [ ] `prefers-reduced-motion` respetado: sin marco giratorio ni transiciones largas.
- [ ] `lang="es"` en `<html>`; etiquetas `<label>` asociadas a cada campo.
- [ ] Todo el editor se puede operar con teclado (cabezal, inicio/fin, exportar).

## 3. Rendimiento (pensando en un celular de gama media)
- [ ] `backdrop-filter` en máximo 1-2 elementos visibles a la vez.
- [ ] Animar solo `transform` y `opacity`; evitar animar `box-shadow` grande o `filter`.
- [ ] Rutas con `React.lazy` (el editor y `wavesurfer` se cargan solo cuando se necesitan).
- [ ] Imágenes y miniaturas con `loading="lazy"` y dimensiones explícitas (sin saltos de layout).
- [ ] Fuentes con `font-display: swap` y solo los pesos usados.
- [ ] Listas largas virtualizadas.
- [ ] Objetivo en Lighthouse móvil: Rendimiento ≥ 85, Accesibilidad ≥ 95, Mejores prácticas ≥ 95.

## 4. Estados que toda pantalla debe cubrir
Cargando (esqueletos, no spinners genéricos), vacío (una frase + acción), error (qué pasó + cómo arreglarlo + reintentar), éxito (confirmación con el mismo verbo del botón), sin conexión con el backend (mensaje claro, no pantalla en blanco).

## 5. Consistencia
- [ ] Solo tokens de color y radios definidos en `tokens.css`; cero hex sueltos en componentes.
- [ ] Un solo set de iconos, un solo componente de botón, un solo formateo de tiempos.
- [ ] Mismo nombre para la misma acción en todos los lugares.
- [ ] Máximo un elemento con brillo por vista.

## 6. Cierre de cada tarea de UI
1. Ejecutar `npm run build` y `npm run lint` sin errores ni advertencias nuevas.
2. Generar y revisar las capturas de los 5 tamaños.
3. Pasar la lista de arriba y corregir lo que falle.
4. Resumir en 5 líneas qué se hizo, qué se verificó y qué falta. Hacer commit.
