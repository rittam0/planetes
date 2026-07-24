import { useEffect, useRef, useState } from 'react'
import { usePlanetesStore } from '../store'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export function useObjects() {
  const { setObjects, setTotalObjects, searchQuery } = usePlanetesStore()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const hasLoggedFailure = useRef(false)

  useEffect(() => {
    const fetchObjects = async () => {
      try {
        setLoading(true)
        const params = new URLSearchParams()

        if (searchQuery) {
          params.set('search', searchQuery)
        }
        params.set('limit', '2000')

        const [res, asteroidRes] = await Promise.all([
          fetch(`${API_BASE}/objects?${params}`),
          fetch(`${API_BASE}/asteroids`),
        ])
        if (!res.ok) throw new Error(`HTTP ${res.status}`)

        const data = await res.json()
        const asteroidData = asteroidRes.ok ? await asteroidRes.json() : { objects: [] }
        const loadedObjects = [...(data.objects || []), ...(asteroidData.objects || [])]
        setObjects(loadedObjects)
        setTotalObjects(loadedObjects.length)
        setError(null)
        hasLoggedFailure.current = false
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch objects')
        if (!hasLoggedFailure.current) {
          console.error('Orbital data fetch failed:', err)
          hasLoggedFailure.current = true
        }
      } finally {
        setLoading(false)
      }
    }

    fetchObjects()
    // Refresh every 60 seconds
    const interval = setInterval(fetchObjects, 60000)
    return () => clearInterval(interval)
  }, [searchQuery, setObjects, setTotalObjects])

  return { loading, error }
}

export function useObjectDetail(noradId: string | null) {
  const [detail, setDetail] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!noradId) {
      setDetail(null)
      return
    }

    const fetchDetail = async () => {
      setLoading(true)
      try {
        const res = await fetch(`${API_BASE}/objects/${noradId}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        setDetail(data)
      } catch (err) {
        console.error('Detail fetch error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchDetail()
  }, [noradId])

  return { detail, loading }
}

export function useConjunctions() {
  const { setConjunctions, setTotalConjunctions } = usePlanetesStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchConjunctions = async () => {
      try {
        const res = await fetch(`${API_BASE}/conjunctions?limit=100`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        setConjunctions(data.conjunctions || [])
        setTotalConjunctions(data.total || 0)
      } catch (err) {
        console.error('Conjunction fetch error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchConjunctions()
  }, [setConjunctions, setTotalConjunctions])

  return { loading }
}

export async function runInvestigation(selectedObject: object): Promise<any> {
  const res = await fetch(`${API_BASE}/investigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ selected_object: selectedObject })
  })

  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
