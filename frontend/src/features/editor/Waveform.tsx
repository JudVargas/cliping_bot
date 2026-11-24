import * as React from 'react'

export interface WaveformProps {
  moment: import('../../lib/types').Moment
}

export function Waveform({ moment }: WaveformProps) {
  const canvasRef = React.useRef<HTMLCanvasElement>(null)

  React.useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)

    const width = rect.width
    const height = rect.height
    const center = height / 2

    ctx.clearRect(0, 0, width, height)
    ctx.strokeStyle = 'var(--border)'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, center)
    ctx.lineTo(width, center)
    ctx.stroke()

    ctx.strokeStyle = 'var(--accent-text)'
    ctx.lineWidth = 2
    ctx.beginPath()
    let x = 0
    while (x < width) {
      const y = Math.sin(x * 0.02) * 20 + Math.sin(x * 0.05) * 10
      ctx.lineTo(x, center + y)
      x += 2
    }
    ctx.stroke()

    const startX = (moment.start / (moment.end + 10)) * width
    const endX = (moment.end / (moment.end + 10)) * width
    ctx.fillStyle = 'color-mix(in oklab, var(--accent-text) 30%, transparent)'
    ctx.fillRect(startX, 0, endX - startX, height)
    ctx.strokeStyle = 'var(--accent-text)'
    ctx.lineWidth = 2
    ctx.strokeRect(startX, 0, endX - startX, height)
  }, [moment])

  return (
    <div className="surface p-3 rounded-panel border border-line">
      <div className="flex items-center justify-between mb-2 text-xs text-texto-secundario">
        <span>Forma de onda</span>
        <span className="font-mono">{moment.start.toFixed(1)}s – {moment.end.toFixed(1)}s</span>
      </div>
      <canvas ref={canvasRef} className="w-full h-24 cursor-crosshair" />
    </div>
  )
}
