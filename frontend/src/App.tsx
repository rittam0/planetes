import { Scene } from './components/Scene'
import { HUD } from './components/HUD'
import { SearchBar } from './components/SearchBar'
import { DetailPanel } from './components/DetailPanel'
import { useObjects, useConjunctions } from './hooks/useObjects'

function App() {
  const { error: objectsError } = useObjects()
  useConjunctions()

  return (
    <div className="relative w-screen h-screen bg-space overflow-hidden">
      <Scene />
      <HUD />
      <SearchBar />
      <DetailPanel />
      {objectsError && (
        <div className="pointer-events-none absolute bottom-16 left-5 z-20 max-w-xs rounded border border-debris/40 bg-panel/95 px-3 py-2 font-mono text-[10px] text-debris">
          Orbital data temporarily unavailable
        </div>
      )}
    </div>
  )
}

export default App
