import { create } from 'zustand'

export interface OrbitalObject {
  norad_id: string
  name: string
  category: 'active_satellite' | 'debris' | 'rocket_body' | 'asteroid'
  altitude_km: number
  velocity_kms: number
  latitude: number
  longitude: number
  inclination_deg: number
  period_min: number
}

export interface ConjunctionEvent {
  id: string
  primary_norad: string
  primary_name: string
  secondary_norad: string
  secondary_name: string
  tca: string
  max_probability: number
  min_range_km: number
  relative_velocity_kms: number
}

export interface InvestigationResult {
  investigation_id: string
  conjunction_id: string
  report: string
  sources_verified: boolean
  generated_at: string
  latency_ms: number
}

interface PlanetesState {
  // Data
  objects: OrbitalObject[]
  selectedObject: OrbitalObject | null
  conjunctions: ConjunctionEvent[]
  investigation: InvestigationResult | null
  isInvestigating: boolean

  // UI State
  activeFilters: Set<string>
  searchQuery: string
  showDetailPanel: boolean
  showInvestigationPanel: boolean

  // Stats
  totalObjects: number
  totalConjunctions: number

  // Actions
  setObjects: (objects: OrbitalObject[]) => void
  selectObject: (obj: OrbitalObject | null) => void
  setConjunctions: (conjunctions: ConjunctionEvent[]) => void
  setInvestigation: (result: InvestigationResult | null) => void
  setIsInvestigating: (val: boolean) => void
  toggleFilter: (category: string) => void
  setSearchQuery: (q: string) => void
  setShowDetailPanel: (show: boolean) => void
  setShowInvestigationPanel: (show: boolean) => void
  setTotalObjects: (n: number) => void
  setTotalConjunctions: (n: number) => void
}

export const usePlanetesStore = create<PlanetesState>((set, get) => ({
  objects: [],
  selectedObject: null,
  conjunctions: [],
  investigation: null,
  isInvestigating: false,
  activeFilters: new Set(['active_satellite', 'debris', 'asteroid']),
  searchQuery: '',
  showDetailPanel: false,
  showInvestigationPanel: false,
  totalObjects: 0,
  totalConjunctions: 0,

  setObjects: (objects) => set({ objects }),
  selectObject: (obj) => set({ 
    selectedObject: obj, 
    showDetailPanel: obj !== null,
    showInvestigationPanel: false,
    investigation: null 
  }),
  setConjunctions: (conjunctions) => set({ conjunctions }),
  setInvestigation: (result) => set({ investigation: result }),
  setIsInvestigating: (val) => set({ isInvestigating: val }),
  toggleFilter: (category) => set((state) => {
    const newFilters = new Set(state.activeFilters)
    if (newFilters.has(category)) {
      newFilters.delete(category)
    } else {
      newFilters.add(category)
    }
    return { activeFilters: newFilters }
  }),
  setSearchQuery: (q) => set({ searchQuery: q }),
  setShowDetailPanel: (show) => set({ showDetailPanel: show }),
  setShowInvestigationPanel: (show) => set({ showInvestigationPanel: show }),
  setTotalObjects: (n) => set({ totalObjects: n }),
  setTotalConjunctions: (n) => set({ totalConjunctions: n }),
}))
