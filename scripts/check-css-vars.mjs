// Uso: node scripts/check-css-vars.mjs [carpeta]   (por defecto: src)
// Detecta var(--x) usadas sin definir (causa típica de texto en fuente serif y colores rotos).
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, extname } from 'node:path'

const root = process.argv[2] ?? 'src'
const files = []
;(function walk(d) {
  for (const f of readdirSync(d)) {
    const p = join(d, f)
    if (statSync(p).isDirectory()) { if (f !== 'node_modules') walk(p) }
    else if (['.css', '.tsx', '.ts', '.jsx', '.js'].includes(extname(p))) files.push(p)
  }
})(root)

const defined = new Set()
const used = new Map()
for (const f of files) {
  const t = readFileSync(f, 'utf8')
  for (const m of t.matchAll(/(--[a-z0-9-]+)\s*:/gi)) defined.add(m[1])
  for (const m of t.matchAll(/var\(\s*(--[a-z0-9-]+)\s*(,)?/gi)) {
    if (m[2]) continue // tiene valor de respaldo
    if (!used.has(m[1])) used.set(m[1], new Set())
    used.get(m[1]).add(f)
  }
}
let bad = 0
for (const [v, fs] of used) {
  if (!defined.has(v)) { bad++; console.log(`✗ ${v} se usa sin definirse en: ${[...fs].join(', ')}`) }
}
console.log(bad ? `\n${bad} variable(s) CSS sin definir` : '✓ Todas las variables CSS están definidas')
process.exit(bad ? 1 : 0)
