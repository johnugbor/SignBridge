import { useState, useEffect } from 'react'
import * as THREE from 'three'

export const useAvatarRenderer = (containerId: string) => {
  const [scene, setScene] = useState<THREE.Scene | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    try {
      const container = document.getElementById(containerId)
      if (!container) {
        setError(`Container with id "${containerId}" not found`)
        return
      }

      // Scene setup
      const scene = new THREE.Scene()
      scene.background = new THREE.Color(0xffffff)

      // Camera setup
      const camera = new THREE.PerspectiveCamera(
        75,
        container.clientWidth / container.clientHeight,
        0.1,
        1000
      )
      camera.position.z = 5

      // Renderer setup
      const renderer = new THREE.WebGLRenderer({ antialias: true })
      renderer.setSize(container.clientWidth, container.clientHeight)
      renderer.setPixelRatio(window.devicePixelRatio)
      container.appendChild(renderer.domElement)

      // Add basic avatar (cube placeholder)
      const geometry = new THREE.BoxGeometry(2, 3, 1)
      const material = new THREE.MeshPhongMaterial({ color: 0x0099ff })
      const avatar = new THREE.Mesh(geometry, material)
      scene.add(avatar)

      // Lighting
      const light = new THREE.DirectionalLight(0xffffff, 1)
      light.position.set(5, 10, 7)
      scene.add(light)

      const ambientLight = new THREE.AmbientLight(0xffffff, 0.5)
      scene.add(ambientLight)

      // Animation loop
      const animate = () => {
        requestAnimationFrame(animate)

        // Rotate avatar
        avatar.rotation.y += 0.005

        renderer.render(scene, camera)
      }
      animate()

      // Handle window resize
      const handleResize = () => {
        const width = container.clientWidth
        const height = container.clientHeight
        camera.aspect = width / height
        camera.updateProjectionMatrix()
        renderer.setSize(width, height)
      }

      window.addEventListener('resize', handleResize)

      setScene(scene)

      return () => {
        window.removeEventListener('resize', handleResize)
        container.removeChild(renderer.domElement)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }, [containerId])

  return { scene, error }
}
