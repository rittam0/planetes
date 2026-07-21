#!/bin/bash
set -e
echo "🚀 Starting Planetes migration..."
cd ~/planetes/frontend
echo "📁 In: $(pwd)"

echo "🗑️  Removing Cesium..."
npm uninstall cesium vite-plugin-static-copy 2>/dev/null || true
echo "   ✓ Cesium removed"

echo "📦 Installing Three.js..."
npm install three @types/three
echo "   ✓ Three.js installed"

echo "💾 Backing up old Scene.tsx..."
cp src/components/Scene.tsx src/components/Scene.tsx.cesium.backup 2>/dev/null || true
echo "   ✓ Backup saved"

echo "📝 Writing new Scene.tsx..."
cat > src/components/Scene.tsx << 'SCENE_EOF'
import { useEffect, useRef, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { type OrbitalObject, usePlanetesStore } from '../store'

const EARTH_RADIUS = 6371
const ATMOSPHERE_RADIUS = EARTH_RADIUS * 1.025
const STAR_RADIUS = 500000
const MIN_ZOOM = 6600
const MAX_ZOOM = 50000
const CAMERA_START = 22000

const CATEGORY_COLORS: Record<OrbitalObject['category'], THREE.Color> = {
  active_satellite: new THREE.Color('#00f0ff'),
  debris: new THREE.Color('#ff4444'),
  rocket_body: new THREE.Color('#ffaa00'),
  asteroid: new THREE.Color('#ffffff'),
}

const CATEGORY_SIZES: Record<OrbitalObject['category'], number> = {
  active_satellite: 4,
  debris: 3,
  rocket_body: 4,
  asteroid: 6,
}

function createEarthDayTexture(): THREE.CanvasTexture {
  const size = 2048
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size / 2
  const ctx = canvas.getContext('2d')!

  const oceanGrad = ctx.createLinearGradient(0, 0, 0, size / 2)
  oceanGrad.addColorStop(0, '#0a1a2e')
  oceanGrad.addColorStop(0.3, '#0d2342')
  oceanGrad.addColorStop(0.5, '#0d2b4a')
  oceanGrad.addColorStop(0.7, '#0d2342')
  oceanGrad.addColorStop(1, '#0a1a2e')
  ctx.fillStyle = oceanGrad
  ctx.fillRect(0, 0, size, size / 2)

  ctx.fillStyle = '#1a3a1a'
  const continents = [
    { x: 0.52, y: 0.45, w: 0.12, h: 0.28 },
    { x: 0.60, y: 0.30, w: 0.22, h: 0.25 },
    { x: 0.22, y: 0.28, w: 0.18, h: 0.22 },
    { x: 0.30, y: 0.52, w: 0.10, h: 0.20 },
    { x: 0.78, y: 0.60, w: 0.08, h: 0.10 },
    { x: 0.0, y: 0.88, w: 1.0, h: 0.12 },
    { x: 0.35, y: 0.15, w: 0.04, h: 0.06 },
  ]

  for (const c of continents) {
    ctx.beginPath()
    ctx.ellipse(c.x * size, c.y * size / 2, c.w * size / 2, c.h * size / 4, 0, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = '#2a4a2a'
    ctx.beginPath()
    ctx.ellipse(c.x * size, c.y * size / 2, c.w * size / 3, c.h * size / 6, 0, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = '#1a3a1a'
  }

  ctx.strokeStyle = '#3d2f1f'
  ctx.lineWidth = 3
  const ranges = [
    { x1: 0.55, y1: 0.50, x2: 0.65, y2: 0.35 },
    { x1: 0.25, y1: 0.35, x2: 0.32, y2: 0.50 },
    { x1: 0.28, y1: 0.55, x2: 0.35, y2: 0.70 },
  ]
  for (const r of ranges) {
    ctx.beginPath()
    ctx.moveTo(r.x1 * size, r.y1 * size / 2)
    ctx.lineTo(r.x2 * size, r.y2 * size / 2)
    ctx.stroke()
  }

  ctx.fillStyle = '#e8eef5'
  ctx.beginPath()
  ctx.ellipse(size / 2, size / 40, size / 3, size / 30, 0, 0, Math.PI * 2)
  ctx.fill()
  ctx.beginPath()
  ctx.ellipse(size / 2, size / 2 - size / 40, size / 2.5, size / 25, 0, 0, Math.PI * 2)
  ctx.fill()

  ctx.fillStyle = 'rgba(255, 255, 255, 0.15)'
  for (let i = 0; i < 40; i++) {
    const x = Math.random() * size
    const y = Math.random() * size / 2
    const w = 50 + Math.random() * 200
    const h = 10 + Math.random() * 30
    ctx.beginPath()
    ctx.ellipse(x, y, w, h, Math.random() * Math.PI, 0, Math.PI * 2)
    ctx.fill()
  }

  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  return tex
}

function createNightLightsTexture(): THREE.CanvasTexture {
  const size = 2048
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size / 2
  const ctx = canvas.getContext('2d')!

  ctx.fillStyle = '#000000'
  ctx.fillRect(0, 0, size, size / 2)

  const cities = [
    { lon: 0.29, lat: 0.38, r: 25, intensity: 1.0 },
    { lon: 0.26, lat: 0.35, r: 20, intensity: 0.9 },
    { lon: 0.22, lat: 0.36, r: 22, intensity: 0.95 },
    { lon: 0.24, lat: 0.33, r: 18, intensity: 0.8 },
    { lon: 0.30, lat: 0.32, r: 15, intensity: 0.7 },
    { lon: 0.28, lat: 0.40, r: 16, intensity: 0.75 },
    { lon: 0.52, lat: 0.32, r: 22, intensity: 0.95 },
    { lon: 0.53, lat: 0.34, r: 20, intensity: 0.9 },
    { lon: 0.55, lat: 0.33, r: 24, intensity: 1.0 },
    { lon: 0.56, lat: 0.30, r: 18, intensity: 0.85 },
    { lon: 0.58, lat: 0.28, r: 20, intensity: 0.9 },
    { lon: 0.70, lat: 0.38, r: 28, intensity: 1.0 },
    { lon: 0.72, lat: 0.40, r: 26, intensity: 0.95 },
    { lon: 0.74, lat: 0.42, r: 24, intensity: 0.9 },
    { lon: 0.68, lat: 0.35, r: 22, intensity: 0.85 },
    { lon: 0.65, lat: 0.32, r: 20, intensity: 0.8 },
    { lon: 0.78, lat: 0.38, r: 18, intensity: 0.75 },
    { lon: 0.35, lat: 0.58, r: 18, intensity: 0.8 },
    { lon: 0.33, lat: 0.55, r: 15, intensity: 0.7 },
    { lon: 0.55, lat: 0.50, r: 14, intensity: 0.65 },
    { lon: 0.50, lat: 0.55, r: 12, intensity: 0.6 },
    { lon: 0.60, lat: 0.38, r: 16, intensity: 0.8 },
  ]

  for (const city of cities) {
    const x = city.lon * size
    const y = (0.5 - city.lat) * size
    const r = city.r
    const grad = ctx.createRadialGradient(x, y, 0, x, y, r * 2)
    grad.addColorStop(0, `rgba(255, 240, 200, ${city.intensity})`)
    grad.addColorStop(0.3, `rgba(255, 220, 160, ${city.intensity * 0.6})`)
    grad.addColorStop(0.6, `rgba(255, 200, 120, ${city.intensity * 0.3})`)
    grad.addColorStop(1, 'rgba(255, 180, 100, 0)')
    ctx.fillStyle = grad
    ctx.beginPath()
    ctx.arc(x, y, r * 2, 0, Math.PI * 2)
    ctx.fill()
  }

  ctx.fillStyle = 'rgba(255, 230, 180, 0.4)'
  for (let i = 0; i < 800; i++) {
    const x = Math.random() * size
    const y = Math.random() * size / 2
    const r = 1 + Math.random() * 2
    ctx.beginPath()
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
  }

  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  return tex
}

const atmosphereVertexShader = `
  varying vec3 vNormal;
  varying vec3 vPosition;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vPosition = (modelViewMatrix * vec4(position, 1.0)).xyz;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`

const atmosphereFragmentShader = `
  varying vec3 vNormal;
  varying vec3 vPosition;
  uniform vec3 sunDirection;
  void main() {
    vec3 viewDirection = normalize(-vPosition);
    float fresnel = 1.0 - abs(dot(viewDirection, vNormal));
    fresnel = pow(fresnel, 2.5);
    float sunDot = max(dot(vNormal, sunDirection), 0.0);
    float intensity = fresnel * (0.6 + sunDot * 0.4);
    vec3 atmosphereColor = vec3(0.2, 0.6, 1.0);
    vec3 twilightColor = vec3(0.4, 0.2, 0.6);
    vec3 color = mix(twilightColor, atmosphereColor, sunDot);
    gl_FragColor = vec4(color, intensity * 0.6);
  }
`

function createStarfield() {
  const count = 15000
  const geometry = new THREE.BufferGeometry()
  const positions = new Float32Array(count * 3)
  const colors = new Float32Array(count * 3)
  const sizes = new Float32Array(count)

  const colorPalette = [
    new THREE.Color('#e8f4ff'),
    new THREE.Color('#d4e8ff'),
    new THREE.Color('#fff8e8'),
    new THREE.Color('#ffe8c8'),
    new THREE.Color('#ffd4a8'),
    new THREE.Color('#ffb8a0'),
  ]

  for (let i = 0; i < count; i++) {
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    const r = STAR_RADIUS

    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
    positions[i * 3 + 2] = r * Math.cos(phi)

    const color = colorPalette[Math.floor(Math.random() * colorPalette.length)]
    colors[i * 3] = color.r
    colors[i * 3 + 1] = color.g
    colors[i * 3 + 2] = color.b

    sizes[i] = 0.5 + Math.random() * 2.5
  }

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1))

  const material = new THREE.PointsMaterial({
    size: 1.5,
    vertexColors: true,
    transparent: true,
    opacity: 0.9,
    sizeAttenuation: false,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })

  return new THREE.Points(geometry, material)
}

function createMilkyWay() {
  const geometry = new THREE.PlaneGeometry(STAR_RADIUS * 3, STAR_RADIUS * 0.4, 1, 1)
  
  const canvas = document.createElement('canvas')
  canvas.width = 1024
  canvas.height = 256
  const ctx = canvas.getContext('2d')!
  
  ctx.fillStyle = 'rgba(0, 0, 0, 0)'
  ctx.fillRect(0, 0, 1024, 256)
  
  for (let i = 0; i < 5000; i++) {
    const x = Math.random() * 1024
    const y = 128 + (Math.random() - 0.5) * 80 * Math.exp(-Math.pow((x - 512) / 300, 2))
    const brightness = 0.1 + Math.random() * 0.3
    const r = 1 + Math.random() * 2
    ctx.fillStyle = `rgba(200, 210, 255, ${brightness})`
    ctx.beginPath()
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
  }
  
  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  
  const material = new THREE.MeshBasicMaterial({
    map: tex,
    transparent: true,
    opacity: 0.25,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })
  
  const mesh = new THREE.Mesh(geometry, material)
  mesh.rotation.x = Math.PI / 2.2
  mesh.rotation.z = Math.PI / 6
  return mesh
}

function createTrajectory(object: OrbitalObject): THREE.BufferGeometry {
  const points: THREE.Vector3[] = []
  const inclination = THREE.MathUtils.degToRad(object.inclination_deg)
  const latRad = THREE.MathUtils.degToRad(object.latitude)
  const lonRad = THREE.MathUtils.degToRad(object.longitude)
  const alt = Math.max(0, object.altitude_km)
  const radius = EARTH_RADIUS + alt

  const phase = Math.asin(
    Math.max(-1, Math.min(1, Math.sin(latRad) / Math.max(0.001, Math.abs(Math.sin(inclination)))))
  )

  for (let i = 0; i <= 180; i++) {
    const angle = (i / 180) * Math.PI * 2
    const orbitLat = Math.asin(Math.sin(inclination) * Math.sin(angle + phase))
    const orbitLon = lonRad + angle
    
    const r = radius
    const x = r * Math.cos(orbitLat) * Math.cos(orbitLon)
    const y = r * Math.sin(orbitLat)
    const z = r * Math.cos(orbitLat) * Math.sin(orbitLon)
    points.push(new THREE.Vector3(x, y, z))
  }

  return new THREE.BufferGeometry().setFromPoints(points)
}

export function Scene() {
  const containerRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const rafRef = useRef<number>(0)
  const earthGroupRef = useRef<THREE.Group | null>(null)
  const starsRef = useRef<THREE.Points | null>(null)
  const milkyWayRef = useRef<THREE.Mesh | null>(null)
  const orbitalGroupRef = useRef<THREE.Group | null>(null)
  const selectionGroupRef = useRef<THREE.Group | null>(null)
  const raycasterRef = useRef<THREE.Raycaster | null>(null)
  const mouseRef = useRef<THREE.Vector2>(new THREE.Vector2())
  const pointIndexRef = useRef<Map<string, { category: OrbitalObject['category'], mesh: THREE.Points }>>(new Map())
  
  const objects = usePlanetesStore(state => state.objects)
  const activeFilters = usePlanetesStore(state => state.activeFilters)
  const selectedObject = usePlanetesStore(state => state.selectedObject)
  const selectObject = usePlanetesStore(state => state.selectObject)

  useEffect(() => {
    if (!containerRef.current) return

    const container = containerRef.current
    const width = container.clientWidth
    const height = container.clientHeight

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#02040a')
    sceneRef.current = scene

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, STAR_RADIUS * 2)
    camera.position.set(0, 0, CAMERA_START)
    cameraRef.current = camera

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor('#02040a', 1)
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.0
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.minDistance = MIN_ZOOM
    controls.maxDistance = MAX_ZOOM
    controls.enablePan = false
    controls.rotateSpeed = 0.6
    controls.zoomSpeed = 0.8
    controls.autoRotate = true
    controls.autoRotateSpeed = 0.15
    controlsRef.current = controls

    const ambientLight = new THREE.AmbientLight('#1a2a4a', 0.4)
    scene.add(ambientLight)

    const sunLight = new THREE.DirectionalLight('#fff8e8', 2.0)
    sunLight.position.set(50000, 20000, 30000)
    scene.add(sunLight)

    const backLight = new THREE.DirectionalLight('#2a4a8a', 0.3)
    backLight.position.set(-50000, -10000, -30000)
    scene.add(backLight)

    const earthGroup = new THREE.Group()
    scene.add(earthGroup)
    earthGroupRef.current = earthGroup

    const earthGeometry = new THREE.SphereGeometry(EARTH_RADIUS, 128, 128)
    
    const dayTexture = createEarthDayTexture()
    const earthMaterial = new THREE.MeshPhongMaterial({
      map: dayTexture,
      shininess: 10,
      specular: new THREE.Color('#1a3a5a'),
    })
    const earth = new THREE.Mesh(earthGeometry, earthMaterial)
    earthGroup.add(earth)

    const nightTexture = createNightLightsTexture()
    const nightMaterial = new THREE.MeshBasicMaterial({
      map: nightTexture,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
    const nightLights = new THREE.Mesh(earthGeometry, nightMaterial)
    nightLights.scale.setScalar(1.001)
    earthGroup.add(nightLights)

    const atmosphereGeometry = new THREE.SphereGeometry(ATMOSPHERE_RADIUS, 64, 64)
    const atmosphereMaterial = new THREE.ShaderMaterial({
      vertexShader: atmosphereVertexShader,
      fragmentShader: atmosphereFragmentShader,
      uniforms: {
        sunDirection: { value: new THREE.Vector3(0.8, 0.3, 0.5).normalize() },
      },
      transparent: true,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
    const atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial)
    earthGroup.add(atmosphere)

    const stars = createStarfield()
    scene.add(stars)
    starsRef.current = stars

    const milkyWay = createMilkyWay()
    scene.add(milkyWay)
    milkyWayRef.current = milkyWay

    const orbitalGroup = new THREE.Group()
    scene.add(orbitalGroup)
    orbitalGroupRef.current = orbitalGroup

    const selectionGroup = new THREE.Group()
    scene.add(selectionGroup)
    selectionGroupRef.current = selectionGroup

    raycasterRef.current = new THREE.Raycaster()

    const animate = () => {
      rafRef.current = requestAnimationFrame(animate)
      
      if (starsRef.current && cameraRef.current) {
        starsRef.current.rotation.y = cameraRef.current.rotation.y * 0.1
        starsRef.current.rotation.x = cameraRef.current.rotation.x * 0.05
      }
      
      if (milkyWayRef.current) {
        milkyWayRef.current.rotation.z += 0.00002
      }
      
      if (earthGroupRef.current) {
        earthGroupRef.current.rotation.y += 0.0001
      }
      
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    const handleResize = () => {
      const w = container.clientWidth
      const h = container.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', handleResize)

    const handleClick = (event: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect()
      mouseRef.current.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
      mouseRef.current.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
      
      const raycaster = raycasterRef.current
      const camera = cameraRef.current
      const orbitalGroup = orbitalGroupRef.current
      if (!raycaster || !camera || !orbitalGroup) return
      
      raycaster.setFromCamera(mouseRef.current, camera)
      const intersects = raycaster.intersectObjects(orbitalGroup.children, true)
      
      if (intersects.length > 0) {
        const userData = intersects[0].object.userData
        if (userData?.object) {
          selectObject(userData.object)
        }
      } else {
        selectObject(null)
      }
    }
    renderer.domElement.addEventListener('click', handleClick)

    return () => {
      cancelAnimationFrame(rafRef.current)
      window.removeEventListener('resize', handleResize)
      renderer.domElement.removeEventListener('click', handleClick)
      controls.dispose()
      renderer.dispose()
      container.removeChild(renderer.domElement)
    }
  }, [selectObject])

  useEffect(() => {
    const group = orbitalGroupRef.current
    if (!group) return

    while (group.children.length > 0) {
      const child = group.children[0]
      if (child instanceof THREE.Points) {
        child.geometry.dispose()
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m.dispose())
        } else {
          child.material.dispose()
        }
      }
      group.remove(child)
    }
    pointIndexRef.current.clear()

    const byCategory: Record<OrbitalObject['category'], OrbitalObject[]> = {
      active_satellite: [],
      debris: [],
      rocket_body: [],
      asteroid: [],
    }

    for (const obj of objects.slice(0, 5000)) {
      if (byCategory[obj.category]) {
        byCategory[obj.category].push(obj)
      }
    }

    for (const [category, items] of Object.entries(byCategory)) {
      if (items.length === 0) continue
      
      const geometry = new THREE.BufferGeometry()
      const positions = new Float32Array(items.length * 3)
      const colors = new Float32Array(items.length * 3)
      const sizes = new Float32Array(items.length)
      
      const catColor = CATEGORY_COLORS[category as OrbitalObject['category']]
      const baseSize = CATEGORY_SIZES[category as OrbitalObject['category']]
      
      for (let i = 0; i < items.length; i++) {
        const obj = items[i]
        const r = EARTH_RADIUS + Math.max(0, obj.altitude_km)
        const lat = THREE.MathUtils.degToRad(obj.latitude)
        const lon = THREE.MathUtils.degToRad(obj.longitude)
        
        positions[i * 3] = r * Math.cos(lat) * Math.cos(lon)
        positions[i * 3 + 1] = r * Math.sin(lat)
        positions[i * 3 + 2] = r * Math.cos(lat) * Math.sin(lon)
        
        colors[i * 3] = catColor.r
        colors[i * 3 + 1] = catColor.g
        colors[i * 3 + 2] = catColor.b
        
        sizes[i] = baseSize
      }
      
      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
      geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1))
      
      const material = new THREE.PointsMaterial({
        size: baseSize,
        vertexColors: true,
        transparent: true,
        opacity: 0.9,
        sizeAttenuation: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      })
      
      const points = new THREE.Points(geometry, material)
      points.userData = { category, objects: items }
      points.visible = activeFilters.has(category)
      group.add(points)
      
      for (let i = 0; i < items.length; i++) {
        pointIndexRef.current.set(items[i].norad_id, {
          category: items[i].category,
          mesh: points,
        })
      }
    }
  }, [objects])

  useEffect(() => {
    const group = orbitalGroupRef.current
    if (!group) return
    
    for (const child of group.children) {
      if (child instanceof THREE.Points) {
        const cat = child.userData.category as OrbitalObject['category']
        child.visible = activeFilters.has(cat)
      }
    }
  }, [activeFilters])

  useEffect(() => {
    const group = selectionGroupRef.current
    if (!group) return

    while (group.children.length > 0) {
      const child = group.children[0]
      if (child instanceof THREE.Mesh || child instanceof THREE.Points || child instanceof THREE.Line) {
        child.geometry.dispose()
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m.dispose())
        } else {
          child.material.dispose()
        }
      }
      group.remove(child)
    }

    if (!selectedObject) return

    const r = EARTH_RADIUS + Math.max(0, selectedObject.altitude_km)
    const lat = THREE.MathUtils.degToRad(selectedObject.latitude)
    const lon = THREE.MathUtils.degToRad(selectedObject.longitude)
    const pos = new THREE.Vector3(
      r * Math.cos(lat) * Math.cos(lon),
      r * Math.sin(lat),
      r * Math.cos(lat) * Math.sin(lon)
    )

    const ringGeometry = new THREE.RingGeometry(8, 12, 32)
    const ringMaterial = new THREE.MeshBasicMaterial({
      color: '#d2c6ae',
      transparent: true,
      opacity: 0.8,
      side: THREE.DoubleSide,
    })
    const ring = new THREE.Mesh(ringGeometry, ringMaterial)
    ring.position.copy(pos)
    ring.lookAt(0, 0, 0)
    group.add(ring)

    const trajGeometry = createTrajectory(selectedObject)
    const trajMaterial = new THREE.LineBasicMaterial({
      color: '#4c93c3',
      transparent: true,
      opacity: 0.5,
    })
    const trajectory = new THREE.Line(trajGeometry, trajMaterial)
    group.add(trajectory)
  }, [selectedObject])

  return (
    <div ref={containerRef} className="absolute inset-0" style={{ background: '#02040a' }} />
  )
}
SCENE_EOF
echo "   ✓ New Scene.tsx written"

echo "⚙️  Updating vite.config.ts..."
cat > vite.config.ts << 'VITE_EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  }
})
VITE_EOF
echo "   ✓ vite.config.ts updated"

echo "🧹 Cleaning main.tsx..."
if grep -q "cesium" src/main.tsx 2>/dev/null; then
    sed -i '/cesium/d' src/main.tsx
    echo "   ✓ Removed Cesium CSS import"
else
    echo "   ℹ️  Already clean"
fi

echo "🧹 Removing old env files..."
rm -f .env .env.local 2>/dev/null || true
echo "   ✓ Removed"

echo "🧹 Clearing cache..."
rm -rf node_modules/.vite dist 2>/dev/null || true
echo "   ✓ Cache cleared"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ DONE! Now run: npm run dev"
echo "Then open: http://localhost:3000"
echo "═══════════════════════════════════════════════════════════════"
