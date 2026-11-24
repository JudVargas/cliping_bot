import { test, expect } from '@playwright/test'

const sizes = [
  { name: 'movil-320', width: 320, height: 740 },
  { name: 'movil-360', width: 360, height: 740 },
  { name: 'movil-390', width: 390, height: 844 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'laptop-1024', width: 1024, height: 768 },
  { name: 'desktop-1440', width: 1440, height: 900 },
]

const routes = ['/', '/videos/demo', '/clips/demo', '/ajustes']

for (const s of sizes) {
  for (const r of routes) {
    test(`${s.name} ${r}`, async ({ page }) => {
      await page.setViewportSize({ width: s.width, height: s.height })
      await page.goto(`http://localhost:5173${r}?mock=extremos`)
      await page.waitForLoadState('networkidle')

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth
      )
      if (overflow) {
        throw new Error(`Scroll horizontal en ${s.name} ${r}`)
      }

      await page.screenshot({
        path: `e2e/shots/${s.name}${r.replace(/\//g, '_')}.png`,
        fullPage: true,
      })
    })
  }
}
