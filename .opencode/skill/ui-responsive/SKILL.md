---
name: ui-responsive
description: Reglas para construir interfaces React que funcionen igual de bien en celular y en computador (mobile-first, breakpoints, navegación adaptable, touch, video vertical, acceso por red local y PWA). Úsalo al crear o modificar cualquier pantalla o componente del frontend.
---

# UI responsive, mobile-first

## Principio
Diseña primero para 360-390 px de ancho y escala hacia arriba. Cada componente debe verse bien y ser usable en: **360, 390, 768, 1024 y 1440 px**. Nunca dejes scroll horizontal en la página.

## Breakpoints (Tailwind)
| Prefijo | Ancho | Uso típico |
|---|---|---|
| (base) | < 640 | celular, 1 columna |
| `sm` | 640 | celular grande / horizontal |
| `md` | 768 | tablet, 2 columnas |
| `lg` | 1024 | computador, aparece rail lateral |
| `xl` | 1280 | 3 paneles en el editor |
| `2xl` | 1536 | limitar ancho máximo del contenido |

Escribe los estilos base para móvil y añade `md:`, `lg:`... solo para ampliar. No uses `max-*` salvo excepciones justificadas.

## Estructura de la app (shell)
- **Móvil (< lg):** barra superior compacta (título + acción principal) y **barra de navegación inferior** con 3-4 destinos (Videos, Clips, Ajustes). Los paneles secundarios se abren como **bottom sheet**, no como columnas.
- **Escritorio (≥ lg):** **rail lateral** izquierdo de 72 px (iconos, se expande a 240 px), contenido central y panel inspector derecho cuando aplique.
- La navegación es una sola fuente de datos (`navItems`) renderizada de dos formas, no dos implementaciones duplicadas.

```tsx
// Shell base
<div className="min-h-dvh bg-bg text-text lg:grid lg:grid-cols-[72px_1fr]">
  <SideRail className="hidden lg:flex" />
  <main className="pb-[calc(4.5rem+env(safe-area-inset-bottom))] lg:pb-0">
    <Outlet />
  </main>
  <BottomNav className="fixed inset-x-0 bottom-0 lg:hidden" />
</div>
```

## Unidades y viewport
- Usa `dvh` / `svh` en lugar de `vh` (la barra del navegador móvil rompe `vh`).
- Respeta zonas seguras: `padding-bottom: env(safe-area-inset-bottom)` en barras fijas. En `index.html`: `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`.
- Tipografía fluida con `clamp()`: `font-size: clamp(1.5rem, 1.1rem + 2vw, 2.5rem)`.
- Espaciado con escala de 4 px; márgenes de página `px-4 md:px-6 lg:px-8`.
- Contenedor de contenido: `mx-auto w-full max-w-screen-2xl`.

## Táctil y puntero
- Objetivos táctiles mínimos **44×44 px** y 8 px de separación entre ellos.
- Nada esencial puede depender de `:hover`. Envuelve hovers en `@media (hover: hover)` (Tailwind: `[@media(hover:hover)]:hover:...`).
- Inputs con `font-size ≥ 16px` (evita el zoom automático de iOS). Usa `inputmode`, `autocomplete` y `type` correctos.
- Gestos (arrastrar el borde de un clip en la línea de tiempo) deben tener alternativa con botones (±0.1 s) para precisión en pantalla táctil y para teclado.
- Usa `touch-action` y `overscroll-behavior` donde haya arrastre horizontal para no pelear con el scroll de la página.

## Listas, tablas y tarjetas
- Adaptar las partes internas de una tarjeta a **su ancho** con container queries (`container-type: inline-size` + `@container`), no con breakpoints de pantalla. Ver `ui-layout-seguro`.
- En móvil, las tablas se convierten en **listas apiladas** (una fila = un bloque con etiqueta/valor), nunca una tabla con scroll horizontal.
- Si una lista puede superar ~100 elementos, virtualiza (`@tanstack/react-virtual`).
- Las cuadrículas usan `grid-cols-1 md:grid-cols-2 xl:grid-cols-3` o `repeat(auto-fill, minmax(18rem, 1fr))`.

## Video y vista previa vertical
- Vista previa 9:16: `aspect-[9/16]` con `max-h-[min(70dvh,48rem)]` y centrada; fondo del reproductor oscuro.
- `<video playsInline preload="metadata" controls>`; no dependas de autoplay con sonido (los móviles lo bloquean).
- Miniaturas: genera un poster por clip en el backend y usa `loading="lazy"` y `decoding="async"`.

## Subida de archivos desde el celular
- `<input type="file" accept="video/*">` visible y grande; la zona de arrastrar y soltar es un extra de escritorio.
- Subida con progreso real (`XMLHttpRequest` o `fetch` con stream), cancelable y con reintento. Si el archivo supera ~500 MB, planear subida por partes.
- El procesamiento largo nunca bloquea la UI: muestra el estado del job (polling cada 2 s o SSE).

## Usar la app desde el celular en la red local
- Vite: `server: { host: true, proxy: { '/api': 'http://localhost:8000' } }` y llama siempre a rutas relativas `/api/...` (nunca `http://localhost:8000` escrito en el código).
- Backend: escuchar en `0.0.0.0` y leer los orígenes CORS permitidos desde `.env`.
- Abrir desde el celular con `http://<IP-del-PC>:5173` (misma red Wi-Fi). Avisar en el README del firewall de Windows.

## PWA (instalable en el celular)
- `manifest.webmanifest` con `display: "standalone"`, `theme_color` igual al fondo, iconos 192/512 y maskable.
- `<meta name="theme-color">` y `apple-touch-icon`.
- Service worker mínimo solo para instalar la app; no cachear respuestas de la API.

## Checklist antes de dar una pantalla por terminada
- [ ] Probada a 360, 390, 768, 1024 y 1440 px sin scroll horizontal
- [ ] Todo lo accionable mide ≥ 44 px en móvil
- [ ] Barras fijas respetan `safe-area-inset`
- [ ] No hay `vh` en layouts a pantalla completa
- [ ] Se puede usar solo con teclado y solo con el dedo
- [ ] Estados vacío, cargando y error diseñados para móvil y escritorio
