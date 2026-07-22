import { usePlanetesStore } from '../store'
import { useObjectDetail } from '../hooks/useObjects'
import { X, Satellite, Trash2, Rocket, AlertTriangle, Crosshair, Orbit, Gauge, Timer, Compass } from 'lucide-react'
import { useState } from 'react'
import { InvestigationPanel } from './InvestigationPanel'

export function DetailPanel() {
  const { selectedObject, selectObject } = usePlanetesStore()
  const { detail, loading } = useObjectDetail(selectedObject?.norad_id || null)
  const [showInvestigation, setShowInvestigation] = useState(false)

  if (!selectedObject) return null

  const categoryConfig = {
    active_satellite: { icon: Satellite, color: 'text-satellite', bg: 'bg-satellite/10', label: 'ACTIVE SATELLITE' },
    debris: { icon: Trash2, color: 'text-debris', bg: 'bg-debris/10', label: 'DEBRIS' },
    rocket_body: { icon: Rocket, color: 'text-rocket', bg: 'bg-rocket/10', label: 'ROCKET BODY' },
    asteroid: { icon: AlertTriangle, color: 'text-white', bg: 'bg-white/10', label: 'ASTEROID' },
  }

  const config = categoryConfig[selectedObject.category] || categoryConfig.debris
  const Icon = config.icon

  return (
    <>
      <div className="absolute top-4 bottom-4 right-4 w-80 z-20 animate-slide-in-right">
        <div className="h-full panel border border-white/10 flex flex-col rounded">
          {/* Header */}
          <div className="p-4 border-b border-white/10">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded ${config.bg}`}>
                  <Icon size={20} className={config.color} />
                </div>
                <div>
                  <h2 className="font-display text-xl text-text leading-tight">
                    {selectedObject.name}
                  </h2>
                  <span className={`font-mono text-xs ${config.color}`}>
                    {config.label}
                  </span>
                </div>
              </div>
              <button
                onClick={() => selectObject(null)}
                className="text-text-muted hover:text-text transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            <div className="mt-3 font-mono text-xs text-text-muted">
              NORAD: {selectedObject.norad_id}
            </div>
          </div>

          {/* Orbital Data */}
          <div className="p-4 space-y-4 flex-1 overflow-y-auto custom-scrollbar">
            <div className="grid grid-cols-2 gap-3">
              <DataCard
                icon={Crosshair}
                label="Altitude"
                value={`${selectedObject.altitude_km.toFixed(1)}`}
                unit="km"
                color="text-satellite"
              />
              <DataCard
                icon={Gauge}
                label="Velocity"
                value={`${selectedObject.velocity_kms.toFixed(2)}`}
                unit="km/s"
                color="text-bone"
              />
              <DataCard
                icon={Compass}
                label="Inclination"
                value={`${selectedObject.inclination_deg.toFixed(1)}`}
                unit="°"
                color="text-amber"
              />
              <DataCard
                icon={Timer}
                label="Period"
                value={`${selectedObject.period_min.toFixed(1)}`}
                unit="min"
                color="text-text"
              />
            </div>

            {/* Position */}
            <div className="glass-panel p-4">
              <div className="hud-label mb-2">Current Position</div>
              <div className="font-mono text-sm text-text space-y-1">
                <div className="flex justify-between">
                  <span className="text-text-muted">Latitude</span>
                  <span>{selectedObject.latitude.toFixed(2)}°</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Longitude</span>
                  <span>{selectedObject.longitude.toFixed(2)}°</span>
                </div>
              </div>
            </div>

            {/* Conjunctions */}
            {detail?.conjunctions && detail.conjunctions.length > 0 && (
              <div>
                <div className="hud-label mb-3">Upcoming Encounters</div>
                <div className="space-y-2">
                  {detail.conjunctions.slice(0, 3).map((conj: any) => (
                    <div key={conj.id} className="glass-panel p-3">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-sm text-text">
                          vs {conj.secondary_name}
                        </span>
                        <span className={`font-mono text-xs ${
                          conj.max_probability > 1e-4 ? 'text-debris' :
                          conj.max_probability > 1e-6 ? 'text-amber' : 'text-satellite'
                        }`}>
                          {conj.max_probability > 1e-4 ? 'HIGH' :
                           conj.max_probability > 1e-6 ? 'MOD' : 'LOW'}
                        </span>
                      </div>
                      <div className="font-mono text-xs text-text-muted mt-1">
                        Miss: {conj.min_range_km.toFixed(3)} km · 
                        Rel: {conj.relative_velocity_kms.toFixed(2)} km/s
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Investigate Button */}
            {detail?.conjunctions && detail.conjunctions.length > 0 && (
              <button
                onClick={() => setShowInvestigation(true)}
                className="w-full btn-primary justify-center py-3"
              >
                <Orbit size={16} />
                Investigate with AI
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Investigation Overlay */}
      {showInvestigation && detail?.conjunctions?.[0] && (
        <InvestigationPanel
          conjunction={detail.conjunctions[0]}
          onClose={() => setShowInvestigation(false)}
        />
      )}
    </>
  )
}

function DataCard({ icon: Icon, label, value, unit, color }: {
  icon: any
  label: string
  value: string
  unit: string
  color: string
}) {
  return (
    <div className="glass-panel p-3">
      <div className="flex items-center gap-2 mb-1">
        <Icon size={12} className={color} />
        <span className="hud-label">{label}</span>
      </div>
      <div className="font-mono text-lg text-text">
        {value}
        <span className="text-sm text-text-muted ml-1">{unit}</span>
      </div>
    </div>
  )
}
