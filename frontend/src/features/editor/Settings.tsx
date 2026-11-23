import * as React from 'react'
import { Input } from '../../components/ui/Button' // placeholder, se usará Input real

export function SettingsPage() {
  return (
    <div className="p-4 md:p-6 max-w-lg mx-auto">
      <h1 className="font-sora font-semibold text-xl text-ink mb-6">Ajustes</h1>
      <div className="surface p-4 rounded-panel border border-line space-y-4">
        <div>
          <label className="block text-xs font-semibold text-ink-muted mb-1">Modelo Whisper</label>
          <select className="input w-full">
            <option>medium</option>
            <option>large-v3</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-ink-muted mb-1">Proveedor LLM</label>
          <select className="input w-full">
            <option>OpenAI</option>
            <option>OpenRouter</option>
            <option>Ollama (local)</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-ink-muted mb-1">Estilo de subtítulos por defecto</label>
          <select className="input w-full">
            <option>clasico</option>
            <option>resaltado</option>
            <option>minimal</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-ink-muted mb-1">Carpeta de salida</label>
          <div className="input pl-3">
            ./data/clips
          </div>
        </div>
      </div>
      <div className="mt-6 text-center">
        <button className="text-xs text-ink-muted underline">Guardar cambios</button>
      </div>
    </div>
  )
}
