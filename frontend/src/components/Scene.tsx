import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { type OrbitalObject, usePlanetesStore } from '../store'

const EARTH_RADIUS = 6371
const ATMOSPHERE_RADIUS = EARTH_RADIUS * 1.03
const STAR_RADIUS = 500000
const MIN_ZOOM = 6600
const MAX_ZOOM = 150000
const CAMERA_START = 22000
const ASTEROID_MIN_RADIUS = 60000
const ASTEROID_MAX_RADIUS = 90000

const CATEGORY_COLORS: Record<OrbitalObject['category'], THREE.Color> = {
  active_satellite: new THREE.Color('#4ade80'),
  debris: new THREE.Color('#f87171'),
  rocket_body: new THREE.Color('#a78bfa'),
  asteroid: new THREE.Color('#f59e0b'),
}

const CATEGORY_SIZES: Record<OrbitalObject['category'], number> = {
  active_satellite: 8,
  debris: 5,
  rocket_body: 6,
  asteroid: 12,
}

// ─── Custom Point Shader — Visible at All Distances ───
const pointVertexShader = `
  attribute float pointSize;
  attribute vec3 pointColor;
  varying vec3 vColor;
  void main() {
    vColor = pointColor;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    float distanceScaledSize = pointSize * (300.0 / -mvPosition.z);
    float minimumVisibleSize = pointSize * 0.9;
    gl_PointSize = max(minimumVisibleSize, distanceScaledSize);
    gl_Position = projectionMatrix * mvPosition;
  }
`

const pointFragmentShader = `
  varying vec3 vColor;
  void main() {
    float dist = length(gl_PointCoord - vec2(0.5));
    if (dist > 0.5) discard;

    float softEdge = 1.0 - smoothstep(0.30, 0.50, dist);
    float glow = 1.0 - smoothstep(0.0, 0.50, dist);
    float alpha = max(softEdge, glow * 0.55);

    gl_FragColor = vec4(vColor, alpha);
  }
`

// ─── Procedural Earth Texture ───
function createEarthTexture(): THREE.CanvasTexture {
  const size = 2048
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size / 2
  const ctx = canvas.getContext('2d')!

  const oceanGrad = ctx.createLinearGradient(0, 0, 0, size / 2)
  oceanGrad.addColorStop(0, '#3a7ab8')
  oceanGrad.addColorStop(0.3, '#4a8ec8')
  oceanGrad.addColorStop(0.5, '#5a9ed8')
  oceanGrad.addColorStop(0.7, '#4a8ec8')
  oceanGrad.addColorStop(1, '#3a7ab8')
  ctx.fillStyle = oceanGrad
  ctx.fillRect(0, 0, size, size / 2)

  ctx.fillStyle = '#7ab87a'
  const continents = [
    {x:0.16,y:0.20,w:0.18,h:0.16}, {x:0.28,y:0.38,w:0.08,h:0.24},
    {x:0.48,y:0.30,w:0.12,h:0.22}, {x:0.48,y:0.20,w:0.10,h:0.08},
    {x:0.58,y:0.16,w:0.26,h:0.22}, {x:0.80,y:0.58,w:0.10,h:0.07},
  ]
  for (const c of continents) {
    ctx.beginPath()
    ctx.ellipse(c.x*size, c.y*size/2, c.w*size, c.h*size/2, 0, 0, Math.PI*2)
    ctx.fill()
  }

  ctx.fillStyle = '#e8f0f8'
  ctx.beginPath()
  ctx.ellipse(size/2, size/2-size/30, size/2.3, size/20, 0, 0, Math.PI*2)
  ctx.fill()

  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  return tex
}

// ─── Atmosphere Shader ───
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
    fresnel = pow(fresnel, 3.5);
    float sunDot = max(dot(vNormal, sunDirection), 0.0);
    float intensity = fresnel * (0.3 + sunDot * 0.2);
    vec3 atmosphereColor = vec3(0.3, 0.6, 0.95);
    vec3 twilightColor = vec3(0.4, 0.3, 0.6);
    vec3 color = mix(twilightColor, atmosphereColor, sunDot);
    gl_FragColor = vec4(color, intensity * 0.35);
  }
`

// ─── Starfield ───
function createStarfield() {
  const count = 12000
  const geometry = new THREE.BufferGeometry()
  const positions = new Float32Array(count * 3)
  const colors = new Float32Array(count * 3)

  const palette = [
    new THREE.Color('#e8f4ff'), new THREE.Color('#d4e8ff'),
    new THREE.Color('#fff8e8'), new THREE.Color('#ffe8c8'),
  ]

  for (let i = 0; i < count; i++) {
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    const r = STAR_RADIUS
    positions[i*3] = r * Math.sin(phi) * Math.cos(theta)
    positions[i*3+1] = r * Math.sin(phi) * Math.sin(theta)
    positions[i*3+2] = r * Math.cos(phi)
    const c = palette[Math.floor(Math.random() * palette.length)]
    colors[i*3] = c.r; colors[i*3+1] = c.g; colors[i*3+2] = c.b
  }

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

  return new THREE.Points(geometry, new THREE.PointsMaterial({
    size: 1.8, vertexColors: true, transparent: false, opacity: 0.65,
    sizeAttenuation: false, depthWrite: false,
  }))
}

// ─── Trajectory Arc ───
function createTrajectory(object: OrbitalObject): THREE.BufferGeometry {
  const points: THREE.Vector3[] = []
  const inclination = THREE.MathUtils.degToRad(object.inclination_deg)
  const latRad = THREE.MathUtils.degToRad(object.latitude)
  const lonRad = THREE.MathUtils.degToRad(object.longitude)
  const alt = Math.max(0, object.altitude_km)
  const rawRadius = EARTH_RADIUS + alt
  const radius = object.category === 'asteroid'
    ? THREE.MathUtils.clamp(rawRadius, ASTEROID_MIN_RADIUS, ASTEROID_MAX_RADIUS)
    : rawRadius

  const phase = Math.asin(Math.max(-1, Math.min(1,
    Math.sin(latRad) / Math.max(0.001, Math.abs(Math.sin(inclination))))))

  for (let i = 0; i <= 180; i++) {
    const angle = (i / 180) * Math.PI * 2
    const orbitLat = Math.asin(Math.sin(inclination) * Math.sin(angle + phase))
    const orbitLon = lonRad + angle
    const r = radius
    points.push(new THREE.Vector3(
      r * Math.cos(orbitLat) * Math.cos(orbitLon),
      r * Math.sin(orbitLat),
      r * Math.cos(orbitLat) * Math.sin(orbitLon)
    ))
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
  const orbitalGroupRef = useRef<THREE.Group | null>(null)
  const selectionGroupRef = useRef<THREE.Group | null>(null)
  const raycasterRef = useRef<THREE.Raycaster | null>(null)
  const mouseRef = useRef<THREE.Vector2>(new THREE.Vector2())
  const sunDirectionRef = useRef<THREE.Vector3>(new THREE.Vector3(0.8, 0.3, 0.5).normalize())

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
    controls.minPolarAngle = 0
    controls.maxPolarAngle = Math.PI
    controlsRef.current = controls

    const ambientLight = new THREE.AmbientLight('#c8d8e8', 0.5)
    scene.add(ambientLight)

    const sunLight = new THREE.DirectionalLight('#fff8e8', 1.8)
    sunLight.position.set(50000, 20000, 30000)
    scene.add(sunLight)

    const fillLight = new THREE.DirectionalLight('#a8c8e8', 0.4)
    fillLight.position.set(-30000, 10000, -20000)
    scene.add(fillLight)

    const earthGroup = new THREE.Group()
    scene.add(earthGroup)
    earthGroupRef.current = earthGroup

    const earthGeometry = new THREE.SphereGeometry(EARTH_RADIUS, 128, 128)
    const earthTexture = new THREE.TextureLoader().load("/earth.jpg")
    const earthMaterial = new THREE.MeshPhongMaterial({
      map: earthTexture,
      shininess: 30,
      specular: new THREE.Color('#3a7aaa'),
    })
    const earth = new THREE.Mesh(earthGeometry, earthMaterial)
    earthGroup.add(earth)

    const atmosphereGeometry = new THREE.SphereGeometry(ATMOSPHERE_RADIUS, 64, 64)
    const atmosphereMaterial = new THREE.ShaderMaterial({
      vertexShader: atmosphereVertexShader,
      fragmentShader: atmosphereFragmentShader,
      uniforms: {
        sunDirection: { value: sunDirectionRef.current.clone() },
      },
      transparent: false,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
    const atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial)
    earthGroup.add(atmosphere)

    const stars = createStarfield()
    scene.add(stars)
    starsRef.current = stars

    const orbitalGroup = new THREE.Group()
    scene.add(orbitalGroup)
    orbitalGroupRef.current = orbitalGroup

    const selectionGroup = new THREE.Group()
    scene.add(selectionGroup)
    selectionGroupRef.current = selectionGroup

    raycasterRef.current = new THREE.Raycaster()
    raycasterRef.current.params.Points = { threshold: 260 }

    const animate = () => {
      rafRef.current = requestAnimationFrame(animate)

      if (starsRef.current && cameraRef.current) {
        starsRef.current.rotation.y = cameraRef.current.rotation.y * 0.1
        starsRef.current.rotation.x = cameraRef.current.rotation.x * 0.05
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

    // ─── CLICK HANDLER — Direct point-buffer index lookup ───
    const handleClick = (event: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect()
      mouseRef.current.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
      mouseRef.current.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

      const raycaster = raycasterRef.current
      const camera = cameraRef.current
      const orbitalGroup = orbitalGroupRef.current
      if (!raycaster || !camera || !orbitalGroup) return

      raycaster.setFromCamera(mouseRef.current, camera)
      const pointClouds = orbitalGroup.children.filter(
        child => child instanceof THREE.Points && child.visible
      )
      const intersects = raycaster.intersectObjects(pointClouds, false)

      if (intersects.length > 0) {
        const intersection = intersects[0]
        const pointIndex = intersection.index
        const pointObjects = intersection.object.userData.objects as OrbitalObject[]
        const hitObject = pointIndex === undefined ? undefined : pointObjects[pointIndex]
        if (hitObject) {
          selectObject(hitObject)
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

  // ─── Update Orbital Objects — Custom Shader Points ───
  useEffect(() => {
    const group = orbitalGroupRef.current
    if (!group) return

    // Clear existing
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
      if (child instanceof THREE.Mesh) {
        child.geometry.dispose()
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m.dispose())
        } else {
          child.material.dispose()
        }
      }
      group.remove(child)
    }

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
      if (items.length === 0 || !activeFilters.has(category)) continue

      // ─── Custom Shader Points ───
      const geometry = new THREE.BufferGeometry()
      const positions = new Float32Array(items.length * 3)
      const colors = new Float32Array(items.length * 3)
      const sizes = new Float32Array(items.length)

      const catColor = CATEGORY_COLORS[category as OrbitalObject['category']]
      const catSize = CATEGORY_SIZES[category as OrbitalObject['category']]

      for (let i = 0; i < items.length; i++) {
        const obj = items[i]
        const rawRadius = EARTH_RADIUS + Math.max(0, obj.altitude_km)
        const r = obj.category === 'asteroid'
          ? THREE.MathUtils.clamp(rawRadius, ASTEROID_MIN_RADIUS, ASTEROID_MAX_RADIUS)
          : rawRadius
        const lat = THREE.MathUtils.degToRad(obj.latitude)
        const lon = THREE.MathUtils.degToRad(obj.longitude)

        positions[i * 3] = r * Math.cos(lat) * Math.cos(lon)
        positions[i * 3 + 1] = r * Math.sin(lat)
        positions[i * 3 + 2] = r * Math.cos(lat) * Math.sin(lon)

        colors[i * 3] = catColor.r
        colors[i * 3 + 1] = catColor.g
        colors[i * 3 + 2] = catColor.b

        sizes[i] = catSize
      }

      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
      geometry.setAttribute('pointColor', new THREE.BufferAttribute(colors, 3))
      geometry.setAttribute('pointSize', new THREE.BufferAttribute(sizes, 1))

      const material = new THREE.ShaderMaterial({
        vertexShader: pointVertexShader,
        fragmentShader: pointFragmentShader,
        transparent: false,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      })

      const points = new THREE.Points(geometry, material)
      points.userData = { category, objects: items }
      group.add(points)
    }
  }, [objects, activeFilters])

  // ─── Update Selection ───
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

    const rawRadius = EARTH_RADIUS + Math.max(0, selectedObject.altitude_km)
    const r = selectedObject.category === 'asteroid'
      ? THREE.MathUtils.clamp(rawRadius, ASTEROID_MIN_RADIUS, ASTEROID_MAX_RADIUS)
      : rawRadius
    const lat = THREE.MathUtils.degToRad(selectedObject.latitude)
    const lon = THREE.MathUtils.degToRad(selectedObject.longitude)
    const pos = new THREE.Vector3(
      r * Math.cos(lat) * Math.cos(lon),
      r * Math.sin(lat),
      r * Math.cos(lat) * Math.sin(lon)
    )

    const ringGeometry = new THREE.RingGeometry(12, 18, 32)
    const ringMaterial = new THREE.MeshBasicMaterial({
      color: '#60a5fa',
      transparent: false,
      opacity: 0.8,
      side: THREE.DoubleSide,
    })
    const ring = new THREE.Mesh(ringGeometry, ringMaterial)
    ring.position.copy(pos)
    ring.lookAt(0, 0, 0)
    group.add(ring)

    const trajGeometry = createTrajectory(selectedObject)
    const trajMaterial = new THREE.LineBasicMaterial({
      color: '#60a5fa',
      transparent: false,
      opacity: 1.0,
    })
    group.add(new THREE.Line(trajGeometry, trajMaterial))
  }, [selectedObject])

  return (
    <div ref={containerRef} className="absolute inset-0" style={{ background: '#02040a' }} />
  )
}
