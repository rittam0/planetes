import { useEffect, useState } from 'react'
import { X, Loader2, CheckCircle, AlertCircle, FileText } from 'lucide-react'
import { runInvestigation } from '../hooks/useObjects'
import type { OrbitalObject } from '../store'

export function InvestigationPanel({ selectedObject, onClose }: {
  selectedObject: OrbitalObject
  onClose: () => void
}) {
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const investigate = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await runInvestigation(selectedObject)
        if (active) setResult(response)
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Investigation unavailable')
        }
      } finally {
        if (active) setLoading(false)
      }
    }
    investigate()
    return () => { active = false }
  }, [selectedObject])

  return (
    <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-[600px] max-h-[80vh] investigation-panel animate-fade-in">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <FileText size={20} className="text-bone" />
            <h3 className="font-display text-xl text-text">Object analysis</h3>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text">
            <X size={20} />
          </button>
        </div>

        <div className="glass-panel p-4 mb-4">
          <div className="font-mono text-sm text-text">{selectedObject.name}</div>
          <div className="font-mono text-xs text-text-muted mt-1">
            Source: {selectedObject.source} · Analysis: supplied selected object
          </div>
        </div>

        {loading && (
          <div className="flex flex-col items-center py-12">
            <Loader2 size={32} className="text-bone animate-spin mb-4" />
            <p className="font-mono text-sm text-text-muted">Analyzing supplied data...</p>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-3 p-4 bg-debris/10 border border-debris/30 rounded">
            <AlertCircle size={16} className="text-debris" />
            <span className="font-mono text-sm text-debris">{error}</span>
          </div>
        )}

        {result && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-satellite" />
              <span className="font-mono text-xs text-satellite">
                {result.llm_enabled ? 'Structured AI report' : 'Validated deterministic report'}
              </span>
            </div>
            <div className="font-mono text-sm text-text whitespace-pre-wrap leading-relaxed">
              {result.report}
            </div>
            <div className="source-citation">
              Sources: {result.sources?.length ? result.sources.join(', ') : 'No authoritative source supplied'}
              {' · '}Validation: {result.output_validated ? 'passed' : 'fallback'}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
