import { useState } from 'react'
import { Search, X } from 'lucide-react'
import { usePlanetesStore } from '../store'

export function SearchBar() {
  const [query, setQuery] = useState('')
  const { setSearchQuery } = usePlanetesStore()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchQuery(query)
  }

  const handleClear = () => {
    setQuery('')
    setSearchQuery('')
  }

  return (
    <form onSubmit={handleSubmit} className="absolute top-5 right-5 z-20">
      <div className="control-panel flex items-center gap-2 px-3 py-2 w-72">
        <Search size={16} className="text-text-muted" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Name or NORAD ID"
          className="bg-transparent border-none outline-none text-sm text-text font-mono w-full placeholder:text-text-muted"
        />
        {query && (
          <button type="button" onClick={handleClear} className="text-text-muted hover:text-text">
            <X size={14} />
          </button>
        )}
      </div>
    </form>
  )
}
