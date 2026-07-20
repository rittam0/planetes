import { useEffect, useRef, useState } from 'react'
import {
  ArcGisMapServerImageryProvider,
  BlendOption,
  Cartesian2,
  Cartesian3,
  Color,
  Credit,
  createWorldImageryAsync,
  EllipsoidTerrainProvider,
  ImageryLayer,
  Ion,
  IonWorldImageryStyle,
  Math as CesiumMath,
  NearFarScalar,
  PointPrimitive,
  PointPrimitiveCollection,
  PolylineCollection,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  UrlTemplateImageryProvider,
  Viewer,
} from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import { type OrbitalObject, usePlanetesStore } from '../store'

const CATEGORY_COLORS: Record<OrbitalObject['category'], Color> = {
  active_satellite: Color.fromCssColorString('#a39f96'),
  debris: Color.fromCssColorString('#6f2922'),
  rocket_body: Color.fromCssColorString('#77685b'),
  asteroid: Color.fromCssColorString('#b8b0a1'),
}

const CATEGORY_SIZES: Record<OrbitalObject['category'], number> = {
  active_satellite: 4,
  debris: 3,
  rocket_body: 4,
  asteroid: 5,
}

type CategoryCollections = Record<OrbitalObject['category'], PointPrimitiveCollection>
type PointIndex = Map<string, { category: OrbitalObject['category']; point: PointPrimitive }>

function isOrbitalObject(value: unknown): value is OrbitalObject {
  if (!value || typeof value !== 'object') return false
  return typeof (value as OrbitalObject).norad_id === 'string'
}

function createTrajectory(object: OrbitalObject) {
  const positions: Cartesian3[] = []
  const inclination = CesiumMath.toRadians(object.inclination_deg)
  const latitude = CesiumMath.toRadians(object.latitude)
  const phase = Math.asin(
    Math.max(-1, Math.min(1, Math.sin(latitude) / Math.max(0.001, Math.abs(Math.sin(inclination))))),
  )

  for (let index = 0; index <= 180; index++) {
    const angle = (index / 180) * Math.PI * 2
    const orbitLatitude = Math.asin(Math.sin(inclination) * Math.sin(angle + phase))
    const orbitLongitude = object.longitude + CesiumMath.toDegrees(angle)
    positions.push(
      Cartesian3.fromDegrees(
        orbitLongitude,
        CesiumMath.toDegrees(orbitLatitude),
        object.altitude_km * 1000,
      ),
    )
  }

  return positions
}

export function Scene() {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<Viewer | null>(null)
  const collectionsRef = useRef<CategoryCollections | null>(null)
  const pointsRef = useRef<PointIndex>(new Map())
  const selectionRef = useRef<PointPrimitiveCollection | null>(null)
  const trajectoryRef = useRef<PolylineCollection | null>(null)
  const [imageryNotice, setImageryNotice] = useState<string | null>(null)
  const objects = usePlanetesStore(state => state.objects)
  const activeFilters = usePlanetesStore(state => state.activeFilters)
  const selectedObject = usePlanetesStore(state => state.selectedObject)
  const selectObject = usePlanetesStore(state => state.selectObject)

  useEffect(() => {
    if (!containerRef.current) return

    const token = import.meta.env.VITE_CESIUM_ION_TOKEN?.trim()
    if (token) Ion.defaultAccessToken = token

    const viewer = new Viewer(containerRef.current, {
      animation: false,
      baseLayer: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      navigationHelpButton: false,
      sceneModePicker: false,
      selectionIndicator: false,
      scene3DOnly: true,
      skyBox: false,
      timeline: false,
      terrainProvider: new EllipsoidTerrainProvider(),
      shouldAnimate: false,
      requestRenderMode: true,
      maximumRenderTimeChange: 60,
      orderIndependentTranslucency: false,
      msaaSamples: 2,
      useBrowserRecommendedResolution: true,
      contextOptions: {
        webgl: {
          alpha: true,
          antialias: true,
        },
      },
    })
    viewerRef.current = viewer

    viewer.scene.globe.maximumScreenSpaceError = 1.5
    viewer.scene.globe.tileCacheSize = 220
    viewer.scene.globe.preloadSiblings = false
    viewer.scene.globe.showGroundAtmosphere = true
    viewer.scene.globe.enableLighting = true
    viewer.scene.globe.dynamicAtmosphereLighting = true
    viewer.scene.globe.dynamicAtmosphereLightingFromSun = true
    viewer.scene.globe.lightingFadeOutDistance = 6_500_000
    viewer.scene.globe.lightingFadeInDistance = 18_000_000
    viewer.scene.globe.nightFadeOutDistance = 4_000_000
    viewer.scene.globe.nightFadeInDistance = 14_000_000
    viewer.scene.globe.baseColor = Color.fromCssColorString('#07111b')
    viewer.scene.postProcessStages.fxaa.enabled = true
    viewer.scene.highDynamicRange = false
    viewer.scene.backgroundColor = Color.TRANSPARENT
    viewer.resolutionScale = Math.min(window.devicePixelRatio || 1, 1.5)

    const controls = viewer.scene.screenSpaceCameraController
    controls.enableRotate = true
    controls.enableZoom = true
    controls.enableTilt = true
    controls.enableLook = true
    controls.enableCollisionDetection = true
    controls.inertiaSpin = 0.94
    controls.inertiaZoom = 0.8
    controls.zoomFactor = 3.2
    controls.maximumMovementRatio = 0.3
    controls.minimumZoomDistance = 100_000
    controls.maximumZoomDistance = 70_000_000

    viewer.camera.setView({
      destination: Cartesian3.fromDegrees(12, 24, 22_000_000),
      orientation: {
        heading: 0,
        pitch: CesiumMath.toRadians(-90),
        roll: 0,
      },
    })

    const categories = Object.keys(CATEGORY_COLORS) as OrbitalObject['category'][]
    const collections = Object.fromEntries(
      categories.map(category => [
        category,
        viewer.scene.primitives.add(new PointPrimitiveCollection({ blendOption: BlendOption.OPAQUE })),
      ]),
    ) as CategoryCollections
    collectionsRef.current = collections
    selectionRef.current = viewer.scene.primitives.add(
      new PointPrimitiveCollection({ blendOption: BlendOption.OPAQUE }),
    )
    trajectoryRef.current = viewer.scene.primitives.add(new PolylineCollection())

    const pickHandler = new ScreenSpaceEventHandler(viewer.scene.canvas)
    pickHandler.setInputAction((event: { position: Cartesian2 }) => {
      const picked = viewer.scene.pick(event.position)
      if (isOrbitalObject(picked?.id)) selectObject(picked.id)
    }, ScreenSpaceEventType.LEFT_CLICK)

    let disposed = false
    const loadImagery = async () => {
      let baseLayer: ImageryLayer

      if (token) {
        try {
          const provider = await createWorldImageryAsync({
            style: IonWorldImageryStyle.AERIAL,
          })
          baseLayer = new ImageryLayer(provider)
        } catch (error) {
          console.error('Cesium World Imagery failed:', error)
          if (disposed) return
          setImageryNotice('Cesium World Imagery unavailable · using aerial fallback')
          baseLayer = await createFallbackImageryLayer()
        }
      } else {
        setImageryNotice('Cesium ion token missing · using aerial fallback')
        baseLayer = await createFallbackImageryLayer()
      }

      if (!disposed) {
        baseLayer.brightness = 1
        baseLayer.contrast = 1.02
        baseLayer.saturation = 1.04
        baseLayer.gamma = 1
        baseLayer.dayAlpha = 1
        baseLayer.nightAlpha = 0.48
        viewer.imageryLayers.add(baseLayer)

        const nightLights = new ImageryLayer(
          new UrlTemplateImageryProvider({
            url: 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_CityLights_2012/default//GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg',
            maximumLevel: 8,
            credit: new Credit('NASA Global Imagery Browse Services (GIBS)'),
          }),
        )
        nightLights.dayAlpha = 0
        nightLights.nightAlpha = 0.78
        nightLights.brightness = 1.16
        nightLights.contrast = 1.18
        nightLights.saturation = 0.82
        nightLights.gamma = 0.9
        viewer.imageryLayers.add(nightLights)
        viewer.scene.requestRender()
      }
    }
    void loadImagery()

    return () => {
      disposed = true
      pickHandler.destroy()
      collectionsRef.current = null
      pointsRef.current.clear()
      selectionRef.current = null
      trajectoryRef.current = null
      viewerRef.current = null
      viewer.destroy()
    }
  }, [selectObject])

  useEffect(() => {
    const collections = collectionsRef.current
    if (!collections) return

    const currentIds = new Set<string>()

    for (const object of objects.slice(0, 5000)) {
      const collection = collections[object.category]
      if (!collection) continue
      currentIds.add(object.norad_id)
      const position = Cartesian3.fromDegrees(
        object.longitude,
        object.latitude,
        Math.max(0, object.altitude_km) * 1000,
      )
      const existing = pointsRef.current.get(object.norad_id)

      if (existing?.category === object.category) {
        existing.point.position = position
        existing.point.id = object
        continue
      }

      if (existing) collections[existing.category].remove(existing.point)
      const point = collection.add({
        position,
        pixelSize: CATEGORY_SIZES[object.category],
        color: CATEGORY_COLORS[object.category],
        outlineColor: Color.fromCssColorString('#171513'),
        outlineWidth: 1,
        scaleByDistance: new NearFarScalar(1_000_000, 1.8, 45_000_000, 0.75),
        id: object,
      })
      pointsRef.current.set(object.norad_id, { category: object.category, point })
    }

    for (const [noradId, existing] of pointsRef.current) {
      if (currentIds.has(noradId)) continue
      collections[existing.category].remove(existing.point)
      pointsRef.current.delete(noradId)
    }
    viewerRef.current?.scene.requestRender()
  }, [objects])

  useEffect(() => {
    const collections = collectionsRef.current
    if (!collections) return
    for (const [category, collection] of Object.entries(collections)) {
      collection.show = activeFilters.has(category)
    }
    viewerRef.current?.scene.requestRender()
  }, [activeFilters])

  useEffect(() => {
    const selection = selectionRef.current
    const trajectory = trajectoryRef.current
    if (!selection || !trajectory) return

    selection.removeAll()
    trajectory.removeAll()
    if (!selectedObject) {
      viewerRef.current?.scene.requestRender()
      return
    }

    selection.add({
      position: Cartesian3.fromDegrees(
        selectedObject.longitude,
        selectedObject.latitude,
        Math.max(0, selectedObject.altitude_km) * 1000,
      ),
      pixelSize: 10,
      color: Color.fromCssColorString('#d2c6ae'),
      outlineColor: Color.fromCssColorString('#2f80c2'),
      outlineWidth: 2,
      id: selectedObject,
    })
    trajectory.add({
      positions: createTrajectory(selectedObject),
      width: 1.25,
      material: Color.fromCssColorString('#4c93c3').withAlpha(0.72),
    })
    viewerRef.current?.scene.requestRender()
  }, [selectedObject])

  return (
    <div className="absolute inset-0">
      <ProceduralStars />
      <div ref={containerRef} className="absolute inset-0" />
      {imageryNotice && (
        <div className="pointer-events-none absolute bottom-5 left-5 z-10 max-w-xs rounded border border-amber/30 bg-panel/90 px-3 py-2 font-mono text-[10px] text-amber">
          {imageryNotice}
        </div>
      )}
    </div>
  )
}

async function createFallbackImageryLayer() {
  try {
    const provider = await ArcGisMapServerImageryProvider.fromUrl(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer',
      { enablePickFeatures: false },
    )
    return new ImageryLayer(provider)
  } catch (error) {
    console.error('Aerial imagery fallback failed:', error)
    return createNasaBlueMarbleLayer()
  }
}

function createNasaBlueMarbleLayer() {
  return new ImageryLayer(
    new UrlTemplateImageryProvider({
      url: 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_NextGeneration/default//GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg',
      maximumLevel: 8,
      credit: new Credit('NASA Global Imagery Browse Services (GIBS)'),
    }),
  )
}

function ProceduralStars() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const draw = () => {
      const width = canvas.clientWidth
      const height = canvas.clientHeight
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5)
      canvas.width = Math.max(1, Math.round(width * pixelRatio))
      canvas.height = Math.max(1, Math.round(height * pixelRatio))

      const context = canvas.getContext('2d')
      if (!context) return
      context.fillStyle = '#05070b'
      context.fillRect(0, 0, canvas.width, canvas.height)

      let seed = 0x4f1bbcdc
      const random = () => {
        seed = (seed * 1664525 + 1013904223) >>> 0
        return seed / 0x100000000
      }
      const starCount = Math.max(180, Math.round((width * height) / 7200))

      for (let index = 0; index < starCount; index++) {
        const x = random() * canvas.width
        const y = random() * canvas.height
        const brightness = 0.32 + Math.pow(random(), 2.5) * 0.62
        const radius = (0.38 + Math.pow(random(), 4) * 0.72) * pixelRatio
        const warmth = random()
        context.beginPath()
        context.arc(x, y, radius, 0, Math.PI * 2)
        context.fillStyle = warmth > 0.9
          ? `rgba(238, 222, 194, ${brightness})`
          : `rgba(225, 231, 235, ${brightness})`
        context.fill()
      }
    }

    draw()
    const observer = new ResizeObserver(draw)
    observer.observe(canvas)
    return () => observer.disconnect()
  }, [])

  return <canvas ref={canvasRef} aria-hidden="true" className="absolute inset-0 h-full w-full" />
}
