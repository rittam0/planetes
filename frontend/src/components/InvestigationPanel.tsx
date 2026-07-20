import { useEffect, useState } from 'react'
import { X, Loader2, CheckCircle, AlertCircle, FileText } from 'lucide-react'
import { runInvestigation } from '../hooks/useObjects'

export function InvestigationPanel({ conjunction, onClose }: {
  conjunction: any
  onClose: () => void
}) {
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleInvestigate = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await runInvestigation(conjunction.id)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Investigation failed')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    handleInvestigate()
  }, [conjunction.id])

  return (
    <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-[600px] max-h-[80vh] investigation-panel animate-fade-in">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <FileText size={20} className="text-bone" />
            <h3 className="font-display text-xl text-text">Conjunction analysis</h3>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text">
            <X size={20} />
          </button>
        </div>

        <div className="glass-panel p-4 mb-4">
          <div className="font-mono text-sm text-text">
            {conjunction.primary_name} vs {conjunction.secondary_name}
          </div>
          <div className="font-mono text-xs text-text-muted mt-1">
            TCA: {new Date(conjunction.tca).toLocaleString()} · 
            Miss: {conjunction.min_range_km.toFixed(3)} km
          </div>
        </div>

        {loading && (
          <div className="flex flex-col items-center py-12">
            <Loader2 size={32} className="text-bone animate-spin mb-4" />
            <p className="font-mono text-sm text-text-muted">Analyzing orbital data...</p>
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
                Sources verified · {result.latency_ms}ms
              </span>
            </div>
            <div className="font-mono text-sm text-text whitespace-pre-wrap leading-relaxed">
              {result.report}
            </div>
            <div className="source-citation">
              Sources: NASA NeoWs, CelesTrak SOCRATES, CelesTrak GP
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
