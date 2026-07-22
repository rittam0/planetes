import { usePlanetesStore } from '../store'
import { Satellite, Trash2, AlertTriangle } from 'lucide-react'

export function HUD() {
  const {
    totalConjunctions,
    activeFilters,
    toggleFilter,
    objects,
  } = usePlanetesStore()

  const categories = [
    { key: 'active_satellite', label: 'Satellites', icon: Satellite, color: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/30' },
    { key: 'debris', label: 'Debris', icon: Trash2, color: 'text-red-400', bg: 'bg-red-400/10', border: 'border-red-400/40' },
    { key: 'asteroid', label: 'Asteroids', icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/40' },
  ]

  return (
    <div className="absolute inset-0 pointer-events-none z-10">
      <div className="absolute top-0 left-0 right-0 p-5 grid grid-cols-[1fr_auto_1fr] items-start">
        <div className="pointer-events-auto">
          <h1 className="font-display text-2xl font-medium tracking-[0.12em] text-text">
            PLANETES
          </h1>
          <p className="font-mono text-xs text-text-muted tracking-widest uppercase mt-1">
            Orbital Intelligence
          </p>
          <div className="flex items-center gap-2 mt-2">
            <div className="w-1.5 h-1.5 rounded-full bg-bone animate-pulse" />
            <span className="font-mono text-[10px] tracking-widest text-bone">LIVE</span>
          </div>
        </div>

        <div className="pointer-events-auto flex gap-3">
          <div className="rounded border border-white/10 bg-panel/90 px-4 py-2 text-center">
            <div className="hud-label">Objects</div>
            <div className="hud-value">{objects.length}</div>
          </div>
          <div className="rounded border border-white/10 bg-panel/90 px-5 py-2 text-center min-w-40">
            <div className="hud-label">Encounters</div>
            <div className="hud-value flex items-center justify-center gap-2">
              <AlertTriangle size={14} className="text-amber" />
              {totalConjunctions}
            </div>
          </div>
        </div>

        <div />
      </div>

      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-1 pointer-events-auto rounded border border-white/10 bg-panel/90 p-1">
        {categories.map(cat => {
          const Icon = cat.icon
          const isActive = activeFilters.has(cat.key)
          return (
            <button
              key={cat.key}
              onClick={() => toggleFilter(cat.key)}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-sm font-mono text-xs uppercase tracking-wider
                transition-all duration-200 border
                ${isActive
                  ? `${cat.bg} ${cat.border} ${cat.color}`
                  : 'bg-transparent border-transparent text-text-muted hover:text-text'
                }
              `}
            >
              <Icon size={14} />
              {cat.label}
            </button>
          )
        })}
      </div>

    </div>
  )
}
