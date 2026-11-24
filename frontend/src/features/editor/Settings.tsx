import * as React from 'react'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { Button } from '../../components/ui/Button'
import { Chip } from '../../components/ui/Chip'
import { Save, Mic, Globe, Palette, Folder, Play, CheckCircle2 } from 'lucide-react'

export function SettingsPage() {
  const [whisperModel, setWhisperModel] = React.useState('medium')
  const [llmProvider, setLlmProvider] = React.useState('openai')
  const [subtitleStyle, setSubtitleStyle] = React.useState('clasico')
  const [outputFolder, setOutputFolder] = React.useState('./data/clips')
  const [isSaving, setIsSaving] = React.useState(false)
  const [saved, setSaved] = React.useState(false)

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setSaved(false)
    setTimeout(() => {
      setIsSaving(false)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    }, 1200)
  }

  return (
    <div className="settings-page">
      {/* Hero */}
      <header className="settings-hero">
        <h1 className="settings-hero__title">Ajustes</h1>
        <p className="settings-hero__subtitle">
          Configura las opciones de procesamiento de video, transcripción y exportación de clips.
        </p>
      </header>

      {/* Settings Grid */}
      <div className="settings-grid">
        {/* Whisper Model */}
        <div className="settings-card">
          <div className="settings-card__header">
            <div className="settings-card__icon settings-card__icon--whisper">
              <Mic size={18} strokeWidth={2} />
            </div>
            <h3 className="settings-card__title">Modelo Whisper</h3>
          </div>
          <p className="settings-card__desc">Modelo de transcripción de audio</p>
          <div className="settings-field-group">
            <Select
              label="Modelo de transcripción"
              value={whisperModel}
              onChange={(e) => setWhisperModel(e.target.value)}
            >
              <option value="medium">Medium (rápido y preciso)</option>
              <option value="large-v3">Large-v3 (máxima precisión)</option>
            </Select>
          </div>
        </div>

        {/* LLM Provider */}
        <div className="settings-card">
          <div className="settings-card__header">
            <div className="settings-card__icon settings-card__icon--llm">
              <Globe size={18} strokeWidth={2} />
            </div>
            <h3 className="settings-card__title">Proveedor LLM</h3>
          </div>
          <p className="settings-card__desc">Servidor para detección de momentos con IA</p>
          <div className="settings-field-group">
            <Select
              label="Servidor de momentos"
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value)}
            >
              <option value="openai">OpenAI</option>
              <option value="openrouter">OpenRouter</option>
              <option value="ollama">Ollama (local)</option>
            </Select>
          </div>
        </div>

        {/* Subtitle Style */}
        <div className="settings-card">
          <div className="settings-card__header">
            <div className="settings-card__icon settings-card__icon--subtitles">
              <Palette size={18} strokeWidth={2} />
            </div>
            <h3 className="settings-card__title">Estilo de subtítulos</h3>
          </div>
          <p className="settings-card__desc">Estilo predeterminado para subtítulos quemados</p>
          <div className="settings-field-group">
            <Select
              label="Estilo predeterminado"
              value={subtitleStyle}
              onChange={(e) => setSubtitleStyle(e.target.value)}
            >
              <option value="clasico">Clásico</option>
              <option value="resaltado">Resaltado</option>
              <option value="minimal">Minimal</option>
            </Select>
          </div>
        </div>

        {/* Output Folder */}
        <div className="settings-card settings-card--wide">
          <div className="settings-card__header">
            <div className="settings-card__icon settings-card__icon--output">
              <Folder size={18} strokeWidth={2} />
            </div>
            <h3 className="settings-card__title">Carpeta de salida</h3>
          </div>
          <p className="settings-card__desc">Ruta donde se guardarán los clips renderizados</p>
          <div className="settings-field-group">
            <div className="flex gap-2">
              <Input
                label="Ruta de guardado"
                value={outputFolder}
                onChange={(e) => setOutputFolder(e.target.value)}
                placeholder="./data/clips"
                className="flex-1"
              />
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {}}
                leftIcon={<Folder size={14} strokeWidth={2} />}
              >
                Examinar
              </Button>
            </div>
          </div>
          <p className="text-texto-muted text-[10px] mt-1">
            Los clips se guardarán en esta carpeta
          </p>
        </div>

        {/* System Info */}
        <div className="settings-system-info settings-card">
          <div className="settings-card__header">
            <div className="settings-card__icon settings-card__icon--system">
              <Play size={18} strokeWidth={2} />
            </div>
            <h3 className="settings-card__title">Información del sistema</h3>
          </div>
          <div className="flex flex-col gap-12">
            <div className="settings-system-info__item">
              <div className="settings-system-info__icon">
                <Play size={16} strokeWidth={2} />
              </div>
              <div>
                <p className="settings-system-info__label">GPU</p>
                <p className="settings-system-info__value">GTX 1660 Ti 6GB</p>
              </div>
            </div>
            <div className="settings-system-info__item">
              <div className="settings-system-info__icon">
                <Chip variant="default" size="sm">CUDA</Chip>
              </div>
              <div>
                <p className="settings-system-info__label">Aceleración</p>
                <p className="settings-system-info__value">NVENC disponible</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Save Bar (sticky bottom) */}
      <div className="settings-save-bar">
        <div className="settings-save-bar__inner">
          {saved && (
            <div className="settings-badge settings-badge--saved">
              <CheckCircle2 size={14} strokeWidth={2} />
              Guardado
            </div>
          )}
          {isSaving && (
            <div className="settings-badge settings-badge--saving">
              <AlertCircle size={14} strokeWidth={2} />
              Guardando…
            </div>
          )}
          {!isSaving && !saved && (
            <div className="settings-badge settings-badge--saved">
              <CheckCircle2 size={14} strokeWidth={2} />
              Cambios listos para guardar
            </div>
          )}
          <Button
            variant="primary"
            size="md"
            onClick={handleSave}
            disabled={isSaving}
            leftIcon={<Save size={18} strokeWidth={2} />}
          >
            {isSaving ? 'Guardando...' : 'Guardar cambios'}
          </Button>
        </div>
      </div>
    </div>
  )
}
