---
name: ui-sistema-diseno
description: Sistema de diseño profesional y moderno para ClipForge (grafito con un solo acento cobalto, tipografía IBM Plex, tema oscuro y claro, componentes sobrios). Reemplaza al skill ui-futurista. Úsalo para cualquier decisión de color, tipografía, espaciado, superficies o estilo de componentes.
---

# Sistema de diseño: grafito y cobalto

## Idea rectora
Herramienta de edición seria y precisa, con un aire tecnológico discreto: superficies grafito, **un solo color de acento (cobalto)**, tipografía técnica legible y mucho orden. Lo futurista viene de la precisión y la limpieza, no del neón. Sin brillos, sin degradados decorativos, sin vidrio esmerilado salvo en la barra inferior y las hojas flotantes.

## Qué cambia respecto a la versión anterior
- Se eliminan: violeta, cian y magenta, el verde neón, los brillos (`glow`), el marco giratorio, las etiquetas en MAYÚSCULAS con barra lateral (como "| PROCESAMIENTO"), y las fuentes Sora/Manrope.
- Se usan: grafito neutro, cobalto como único acento, verde/ámbar/rojo solo para estados, IBM Plex Sans y IBM Plex Mono.
- **Borrar la carpeta `.opencode/skill/ui-futurista/`** y reemplazar todo uso de sus tokens por los de este skill.

## Tokens de color

### Tema oscuro (por defecto)
| Token | Hex | Uso |
|---|---|---|
| `--bg` | `#0E1218` | fondo de la app |
| `--surface` | `#151A22` | tarjetas y paneles |
| `--surface-2` | `#1B2230` | elementos elevados, inputs, hover |
| `--border` | `#2A3444` | bordes y divisores |
| `--text` | `#E8ECF2` | texto principal |
| `--text-muted` | `#9AA6B8` | texto secundario |
| `--text-subtle` | `#6B778A` | solo texto decorativo o deshabilitado |
| `--accent` | `#356AD6` | relleno de botón primario, progreso |
| `--accent-hover` | `#2E5DBE` | hover/pressed del primario |
| `--accent-text` | `#7FA6F5` | enlaces y texto de acento sobre fondo oscuro |
| `--success` | `#34D399` | éxito, etapa completada |
| `--warning` | `#F5B94A` | aviso |
| `--danger` | `#F0616D` | error, acción destructiva |

### Tema claro
`--bg #F5F7FA`, `--surface #FFFFFF`, `--surface-2 #EEF2F7`, `--border #DDE3EC`, `--text #141A24`, `--text-muted #566377`, `--accent #2F62D0`, `--accent-text #2F62D0`, `--success #0F9F6E`, `--warning #B7791F`, `--danger #D14343`.

```css
/* src/styles/tokens.css */
:root {
  color-scheme: dark;
  --bg:#0e1218; --surface:#151a22; --surface-2:#1b2230; --border:#2a3444;
  --text:#e8ecf2; --text-muted:#9aa6b8; --text-subtle:#6b778a;
  --accent:#356ad6; --accent-hover:#2e5dbe; --accent-text:#7fa6f5;
  --success:#34d399; --warning:#f5b94a; --danger:#f0616d;

  --radius-field:6px; --radius-card:12px; --radius-pill:999px;
  --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px; --space-5:24px; --space-6:32px;
  --ease:cubic-bezier(.2,.7,.2,1); --dur-fast:120ms; --dur:200ms;

  --font-sans:"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-mono:"IBM Plex Mono", ui-monospace, "SF Mono", Consolas, monospace;
}
:root[data-theme="light"] {
  color-scheme: light;
  --bg:#f5f7fa; --surface:#ffffff; --surface-2:#eef2f7; --border:#dde3ec;
  --text:#141a24; --text-muted:#566377; --text-subtle:#8a95a6;
  --accent:#2f62d0; --accent-hover:#2753b3; --accent-text:#2f62d0;
  --success:#0f9f6e; --warning:#b7791f; --danger:#d14343;
}
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) { /* repetir los valores del tema claro */ }
}
```
Regla: **cero colores hexadecimales sueltos en componentes**; todo sale de variables. Exponerlas en Tailwind (`@theme` en v4 o `theme.extend.colors` en v3) como `bg-surface`, `text-muted`, `border-border`, `bg-accent`.

Contraste: el texto normal debe cumplir ≥ 4.5:1. `--text-subtle` nunca para información importante. Botón primario: texto blanco sobre `--accent`.

## Tipografía
- **IBM Plex Sans** (400, 500, 600) para toda la interfaz. **IBM Plex Mono** (400, 500) solo para datos reales: tiempos `00:12.340`, rutas, tamaños de archivo, IDs.
- Instalar: `npm i @fontsource/ibm-plex-sans @fontsource/ibm-plex-mono` e importar solo los pesos usados en `main.tsx`:
  `import '@fontsource/ibm-plex-sans/400.css'` (y 500, 600), `import '@fontsource/ibm-plex-mono/400.css'`.
- Escala: 12 · 13 · 14 · 16 · 20 · 24 · 32 px. Texto base 14-15 px en móvil y escritorio; títulos de pantalla 24 px (600), títulos de tarjeta 15-16 px (600).
- Interlineado 1.5 en texto, 1.25 en títulos. Tracking normal (máximo `-0.01em` en títulos grandes).
- Títulos de sección en **minúscula normal** (sentence case) y peso 600; **no usar MAYÚSCULAS espaciadas** ni barras decorativas al lado.
- Números que cambian (porcentajes, tiempos): `font-variant-numeric: tabular-nums`.

## Superficies, bordes y elevación
- Jerarquía por **color de superficie + borde de 1 px**, no por sombras: `bg` → `surface` → `surface-2`.
- Tarjeta: `background: var(--surface); border:1px solid var(--border); border-radius: var(--radius-card); padding: 16px (móvil) / 20px (md+)`.
- Una sola sombra permitida, para menús y hojas flotantes: `0 8px 24px rgba(0,0,0,.35)`.
- `backdrop-filter` solo en la barra de navegación inferior y las hojas (bottom sheets).

## Componentes base
- **Botón primario:** relleno `--accent`, texto blanco, radio 6 px, altura 40 px (44 px en móvil), peso 500. Secundario: borde `--border`, fondo transparente. Destructivo: texto `--danger`, borde `--danger` al 40 %. Estado de foco: anillo de 2 px `--accent-text` con separación de 2 px.
- **Badge de estado:** píldora pequeña con punto de color + texto ("Subido", "Procesando", "Listo", "Error"). Fondo = color del estado al 12 % de opacidad, texto = color del estado. Nunca el color como única señal. `flex-shrink: 0` y `white-space: nowrap`.
- **Input:** fondo `--surface-2`, borde `--border`, foco con borde `--accent`. Altura 40-44 px, texto ≥ 16 px en móvil.
- **Barra de progreso:** pista `--surface-2`, relleno `--accent`, 4 px de alto, radio 999 px. Completada: `--success`.
- **Iconos:** `lucide-react`, trazo 1.75, 18-20 px, color `--text-muted` por defecto y `--accent-text` si está activo.

## Movimiento
- Solo transiciones de 120-200 ms en color, borde y opacidad, y en la apertura/cierre de hojas y menús. Nada de animaciones de entrada en cada sección ni hovers elaborados.
- El único movimiento continuo permitido es la barra de progreso de la etapa activa.
- Respetar `prefers-reduced-motion`.

## Texto de la interfaz
Español claro y específico, verbos directos: "Subir video", "Reintentar etapa", "Exportar clip". El mismo nombre para la misma acción en todo el flujo. Errores: qué pasó y cómo solucionarlo, sin disculpas.

## Lista de comprobación de estilo
- [ ] Un solo color de acento en toda la pantalla
- [ ] Sin sombras de colores, sin brillos, sin degradados decorativos
- [ ] Sin textos en mayúsculas con espaciado ni barras decorativas
- [ ] Todo el color sale de variables
- [ ] Se ve bien en tema oscuro y claro
- [ ] Contraste ≥ 4.5:1 en texto normal
