import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import * as THREE from 'three';

// ─── Colores por doc_type ─────────────────────────────────────────────────
const COLORES = {
  articulado: { hex: 0x3B6B9E, css: '#3B6B9E' },
  folleto:    { hex: 0xC8882A, css: '#C8882A' },
  resumen:    { hex: 0x4A9068, css: '#4A9068' },
};
const FALLBACK = { hex: 0x888888, css: '#888888' };

function normalizar(valores, outMin = -8, outMax = 8) {
  const mn = Math.min(...valores);
  const mx = Math.max(...valores);
  const rango = mx - mn || 1;
  return valores.map(v => outMin + ((v - mn) / rango) * (outMax - outMin));
}

function proyectar(pos3d, camera, W, H) {
  const v = pos3d.clone().project(camera);
  return {
    x: (v.x * 0.5 + 0.5) * W,
    y: (-v.y * 0.5 + 0.5) * H,
    visible: v.z < 1,
  };
}

// ─── Tooltip ──────────────────────────────────────────────────────────────
function Tooltip({ point, pos }) {
  if (!point) return null;
  const nombre = point.source
    ?.replace('.pdf', '')
    .replace(/_/g, ' ')
    .replace(/\(\d+\)/, '')
    .trim();
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.1 }}
      style={{
        position: 'fixed', left: pos.x + 16, top: pos.y - 8,
        zIndex: 100, maxWidth: 290, pointerEvents: 'none',
        background: 'rgba(247,244,239,0.96)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255,255,255,0.85)',
        borderRadius: 10, padding: '0.7rem 0.9rem',
        boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
      }}
    >
      <div style={{ fontSize: '0.67rem', color: 'var(--text-tertiary)', marginBottom: '0.3rem', fontWeight: 500 }}>
        {nombre} · pág. {point.page ?? '—'} · {point.año}
      </div>
      <div style={{ display: 'flex', gap: '0.3rem', marginBottom: '0.4rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.62rem', padding: '0.1rem 0.4rem', borderRadius: 20, background: 'rgba(0,0,0,0.06)', color: 'var(--text-secondary)' }}>
          {point.doc_type}
        </span>
        <span style={{ fontSize: '0.62rem', padding: '0.1rem 0.4rem', borderRadius: 20, background: 'rgba(0,0,0,0.06)', color: 'var(--text-secondary)' }}>
          {point.type === 'table' ? '📊 tabla' : '📝 texto'}
        </span>
      </div>
      <p style={{ fontSize: '0.73rem', color: 'var(--text-primary)', lineHeight: 1.5, margin: 0 }}>
        {point.content_preview?.slice(0, 140)}{point.content_preview?.length > 140 ? '…' : ''}
      </p>
    </motion.div>
  );
}

// ─── Leyenda ──────────────────────────────────────────────────────────────
function Leyenda({ activo, setActivo }) {
  return (
    <div style={{
      position: 'absolute', bottom: 24, left: 24, zIndex: 10,
      background: 'rgba(247,244,239,0.88)', backdropFilter: 'blur(16px)',
      border: '1px solid rgba(255,255,255,0.8)',
      borderRadius: 12, padding: '0.75rem 1rem',
      boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
    }}>
      <div style={{ fontSize: '0.62rem', fontWeight: 600, color: 'var(--text-tertiary)', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
        Documento
      </div>
      {Object.entries(COLORES).map(([tipo, col]) => (
        <div key={tipo} onClick={() => setActivo(a => a === tipo ? null : tipo)}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.2rem 0', cursor: 'pointer', userSelect: 'none',
            opacity: activo && activo !== tipo ? 0.3 : 1,
            transition: 'opacity 0.15s',
          }}
        >
          <div style={{ width: 10, height: 10, borderRadius: '50%', background: col.css }} />
          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 500 }}>{tipo}</span>
        </div>
      ))}
      <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(0,0,0,0.06)', fontSize: '0.62rem', color: 'var(--text-tertiary)' }}>
        ● tablas (grandes) &nbsp;·&nbsp; · textos (pequeños)
      </div>
    </div>
  );
}

// ─── Etiquetas de cluster proyectadas ─────────────────────────────────────
function ClusterLabels({ centroides, camera, size }) {
  if (!camera || !size.W || !size.H) return null;
  return (
    <>
      {Object.entries(centroides).map(([tipo, pos3d]) => {
        const col = COLORES[tipo] || FALLBACK;
        const { x, y, visible } = proyectar(pos3d, camera, size.W, size.H);
        if (!visible) return null;
        return (
          <div key={tipo} style={{
            position: 'absolute',
            left: x, top: y,
            transform: 'translate(-50%, -140%)',
            pointerEvents: 'none',
            zIndex: 8,
          }}>
            <div style={{
              background: `${col.css}18`,
              border: `1px solid ${col.css}55`,
              borderRadius: 20,
              padding: '0.18rem 0.65rem',
              fontSize: '0.68rem',
              fontWeight: 600,
              color: col.css,
              backdropFilter: 'blur(8px)',
              whiteSpace: 'nowrap',
              letterSpacing: '0.02em',
            }}>
              {tipo.charAt(0).toUpperCase() + tipo.slice(1)}
            </div>
          </div>
        );
      })}
    </>
  );
}

// ─── Nota explicativa ─────────────────────────────────────────────────────
function NotaExplicativa() {
  const [abierta, setAbierta] = useState(false);
  return (
    <div style={{ position: 'absolute', bottom: 24, right: 24, zIndex: 10, maxWidth: 280 }}>
      <div
        onClick={() => setAbierta(a => !a)}
        style={{
          background: 'rgba(247,244,239,0.88)', backdropFilter: 'blur(16px)',
          border: '1px solid rgba(255,255,255,0.8)',
          borderRadius: 10, padding: '0.5rem 0.85rem',
          cursor: 'pointer', userSelect: 'none',
          display: 'flex', alignItems: 'center', gap: '0.4rem',
        }}
      >
        <span style={{ fontSize: '0.78rem' }}>ℹ</span>
        <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
          ¿Qué muestra este mapa?
        </span>
        <span style={{ fontSize: '0.62rem', color: 'var(--text-tertiary)', marginLeft: 'auto' }}>
          {abierta ? '▲' : '▼'}
        </span>
      </div>
      <AnimatePresence>
        {abierta && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            style={{
              background: 'rgba(247,244,239,0.96)', backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255,255,255,0.85)',
              borderRadius: 10, padding: '0.85rem 1rem',
              marginTop: '0.4rem',
              boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
            }}
          >
            <p style={{ fontSize: '0.73rem', color: 'var(--text-primary)', lineHeight: 1.6, margin: 0 }}>
              Cada punto es un fragmento indexado. Su <strong>posición refleja similitud semántica</strong>: los puntos cercanos hablan de temas parecidos.
            </p>
            <p style={{ fontSize: '0.73rem', color: 'var(--text-secondary)', lineHeight: 1.6, margin: '0.5rem 0 0' }}>
              Los <strong>tres ejes son de orientación espacial</strong>, no unidades de medida. UMAP comprime 3.072 dimensiones en 3; los valores de los ejes no tienen interpretación directa.
            </p>
            <p style={{ fontSize: '0.73rem', color: 'var(--text-secondary)', lineHeight: 1.6, margin: '0.5rem 0 0' }}>
              Lo que importa: <strong>la distancia relativa entre puntos</strong>, no su posición absoluta.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Módulo principal ─────────────────────────────────────────────────────
export default function MapaModule({ apiBase, onChunkClick }) {
  const [puntos, setPuntos]             = useState([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);
  const [hovered, setHovered]           = useState(null);
  const [tooltipPos, setTooltipPos]     = useState({ x: 0, y: 0 });
  const [filtroActivo, setFiltroActivo] = useState(null);
  const [centroides, setCentroides]     = useState({});
  const [canvasSize, setCanvasSize]     = useState({ W: 0, H: 0 });
  const [tick, setTick]                 = useState(0);

  const mountRef   = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef  = useRef(null);
  const rafRef     = useRef(null);
  const meshesRef  = useRef([]);
  const raycaster  = useRef(new THREE.Raycaster());
  const mouse      = useRef(new THREE.Vector2(-9999, -9999));
  const cam        = useRef({ theta: 0.5, phi: 1.1, radius: 22 });
  const isDragging = useRef(false);
  const lastXY     = useRef({ x: 0, y: 0 });
  const hoveredRef = useRef(null);

  // ── Fetch ──
  useEffect(() => {
    axios.get(`${apiBase}/umap`)
      .then(r => { setPuntos(r.data); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [apiBase]);

  // ── Montar Three.js ──
  useEffect(() => {
    if (!puntos.length || !mountRef.current) return;

    const W = mountRef.current.clientWidth;
    const H = mountRef.current.clientHeight;
    setCanvasSize({ W, H });

    const scene    = new THREE.Scene();
    const camera   = new THREE.PerspectiveCamera(55, W / H, 0.1, 1000);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setClearColor(0x000000, 0);
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    scene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const dir = new THREE.DirectionalLight(0xffffff, 0.4);
    dir.position.set(10, 20, 10);
    scene.add(dir);

    // Normalizar coords
    const xs = normalizar(puntos.map(p => p.x));
    const ys = normalizar(puntos.map(p => p.y));
    const zs = normalizar(puntos.map(p => p.z));

    // ── Ejes de orientación (líneas tenues) ──
    const AXIS_LEN = 9;
    const ejes = [
      { vec: new THREE.Vector3(1, 0, 0), color: 0xCC4444 },
      { vec: new THREE.Vector3(0, 1, 0), color: 0x44AA66 },
      { vec: new THREE.Vector3(0, 0, 1), color: 0x4477CC },
    ];
    ejes.forEach(({ vec, color }) => {
      // Línea principal
      const geo = new THREE.BufferGeometry().setFromPoints([
        vec.clone().multiplyScalar(-AXIS_LEN),
        vec.clone().multiplyScalar(AXIS_LEN),
      ]);
      scene.add(new THREE.Line(geo, new THREE.LineBasicMaterial({ color, opacity: 0.18, transparent: true })));

      // Marcas de referencia cada 3 unidades
      const perp = vec.x !== 0
        ? new THREE.Vector3(0, 1, 0)
        : new THREE.Vector3(1, 0, 0);
      for (let t = -AXIS_LEN; t <= AXIS_LEN; t += 3) {
        if (t === 0) continue;
        const center = vec.clone().multiplyScalar(t);
        const tickGeo = new THREE.BufferGeometry().setFromPoints([
          center.clone().addScaledVector(perp, 0.18),
          center.clone().addScaledVector(perp, -0.18),
        ]);
        scene.add(new THREE.Line(tickGeo, new THREE.LineBasicMaterial({ color, opacity: 0.10, transparent: true })));
      }
    });

    // ── Puntos ──
    const geoText  = new THREE.SphereGeometry(0.12, 8, 8);
    const geoTable = new THREE.SphereGeometry(0.19, 10, 10);
    meshesRef.current = [];

    // Calcular centroides por doc_type para etiquetas
    const sums = {}, counts = {};
    puntos.forEach((p, i) => {
      const dt = p.doc_type || 'unknown';
      if (!sums[dt]) { sums[dt] = [0, 0, 0]; counts[dt] = 0; }
      sums[dt][0] += xs[i]; sums[dt][1] += ys[i]; sums[dt][2] += zs[i];
      counts[dt]++;
    });
    const cents = {};
    Object.keys(sums).forEach(dt => {
      cents[dt] = new THREE.Vector3(
        sums[dt][0] / counts[dt],
        sums[dt][1] / counts[dt] + 1.8, // flota sobre el cluster
        sums[dt][2] / counts[dt],
      );
    });
    setCentroides(cents);

    puntos.forEach((p, i) => {
      const col = COLORES[p.doc_type] || FALLBACK;
      const mat = new THREE.MeshPhongMaterial({
        color: col.hex, transparent: true,
        opacity: p.type === 'table' ? 0.88 : 0.72,
        shininess: 60,
      });
      const mesh = new THREE.Mesh(p.type === 'table' ? geoTable : geoText, mat);
      mesh.position.set(xs[i], ys[i], zs[i]);
      scene.add(mesh);
      meshesRef.current.push({ mesh, data: p });
    });

    // Posición inicial cámara
    const { theta, phi, radius } = cam.current;
    camera.position.set(
      radius * Math.sin(phi) * Math.cos(theta),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.sin(theta),
    );
    camera.lookAt(0, 0, 0);

    let frameCount = 0;
    const animate = () => {
      rafRef.current = requestAnimationFrame(animate);
      frameCount++;

      raycaster.current.setFromCamera(mouse.current, camera);
      const hits = raycaster.current.intersectObjects(meshesRef.current.map(m => m.mesh));
      if (hits.length > 0) {
        const found = meshesRef.current.find(m => m.mesh === hits[0].object);
        if (found && hoveredRef.current?.data?.chunk_id !== found.data.chunk_id) {
          hoveredRef.current = found;
          setHovered(found.data);
        }
      } else {
        if (hoveredRef.current) { hoveredRef.current = null; setHovered(null); }
      }

      // Actualizar etiquetas de cluster cada 6 frames
      if (frameCount % 6 === 0) setTick(t => t + 1);

      renderer.render(scene, camera);
    };
    animate();

    const ro = new ResizeObserver(() => {
      if (!mountRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      setCanvasSize({ W: w, H: h });
    });
    ro.observe(mountRef.current);

    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
      renderer.dispose();
      if (mountRef.current?.contains(renderer.domElement)) {
        mountRef.current.removeChild(renderer.domElement);
      }
    };
  }, [puntos]);

  // ── Filtro opacidad ──
  useEffect(() => {
    meshesRef.current.forEach(({ mesh, data }) => {
      const dimmed = filtroActivo && filtroActivo !== data.doc_type;
      mesh.material.opacity = dimmed ? 0.06 : data.type === 'table' ? 0.88 : 0.72;
    });
  }, [filtroActivo]);

  // ── Helpers cámara ──
  const updateCamera = () => {
    const camera = cameraRef.current;
    if (!camera) return;
    const { theta, phi, radius } = cam.current;
    camera.position.set(
      radius * Math.sin(phi) * Math.cos(theta),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.sin(theta),
    );
    camera.lookAt(0, 0, 0);
  };

  // ── Handlers ──
  const onMouseDown  = (e) => { isDragging.current = true; lastXY.current = { x: e.clientX, y: e.clientY }; };
  const onMouseUp    = () => { isDragging.current = false; };
  const onMouseLeave = () => { isDragging.current = false; mouse.current.set(-9999, -9999); setHovered(null); };

  const onMouseMove = (e) => {
    const rect = mountRef.current?.getBoundingClientRect();
    if (rect) {
      mouse.current.x =  ((e.clientX - rect.left)  / rect.width)  * 2 - 1;
      mouse.current.y = -((e.clientY - rect.top)   / rect.height) * 2 + 1;
    }
    setTooltipPos({ x: e.clientX, y: e.clientY });
    if (!isDragging.current) return;
    const dx = e.clientX - lastXY.current.x;
    const dy = e.clientY - lastXY.current.y;
    lastXY.current = { x: e.clientX, y: e.clientY };
    cam.current.theta -= dx * 0.008;
    cam.current.phi    = Math.max(0.15, Math.min(Math.PI - 0.15, cam.current.phi + dy * 0.008));
    updateCamera();
  };

  const onWheel = (e) => {
    e.preventDefault();
    cam.current.radius = Math.max(4, Math.min(60, cam.current.radius * (e.deltaY > 0 ? 1.08 : 0.93)));
    updateCamera();
  };

  const onClick = () => {
    if (!hoveredRef.current) return;
    const { data } = hoveredRef.current;
    onChunkClick({
      chunk_id: data.chunk_id, content: data.content_preview,
      source: data.source, page: data.page,
      type: data.type, doc_type: data.doc_type,
      año: data.año, score: 0,
    });
  };

  if (loading) return <LoadingState />;
  if (error)   return <ErrorState msg={error} />;

  return (
    <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>

      {/* Header */}
      <div style={{
        position: 'absolute', top: 20, left: 24, zIndex: 10,
        background: 'rgba(247,244,239,0.82)', backdropFilter: 'blur(16px)',
        border: '1px solid rgba(255,255,255,0.8)',
        borderRadius: 12, padding: '0.65rem 1rem',
      }}>
        <h2 style={{ fontFamily: 'var(--serif)', fontSize: '1rem', fontWeight: 400, color: 'var(--text-primary)', margin: 0 }}>
          El Mapa del Conocimiento
        </h2>
        <p style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', margin: '0.15rem 0 0' }}>
          {puntos.length} fragmentos · UMAP 3D · drag=girar · scroll=zoom · clic=detalle
        </p>
      </div>

      {/* Canvas Three.js */}
      <div
        ref={mountRef}
        style={{ width: '100%', height: '100%', cursor: isDragging.current ? 'grabbing' : 'grab' }}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseLeave}
        onWheel={onWheel}
        onClick={onClick}
      />

      {/* Etiquetas de cluster proyectadas en 2D — se actualizan con tick */}
      <ClusterLabels
        centroides={centroides}
        camera={cameraRef.current}
        size={canvasSize}
        _tick={tick}
      />

      <Leyenda activo={filtroActivo} setActivo={setFiltroActivo} />
      <NotaExplicativa />

      <AnimatePresence>
        {hovered && <Tooltip key="tt" point={hovered} pos={tooltipPos} />}
      </AnimatePresence>
    </div>
  );
}

function LoadingState() {
  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '0.75rem' }}>
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1.4, repeat: Infinity, ease: 'linear' }}
        style={{ width: 28, height: 28, border: '2px solid rgba(59,107,158,0.15)', borderTop: '2px solid #3B6B9E', borderRadius: '50%' }}
      />
      <span style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)' }}>Cargando mapa 3D…</span>
    </div>
  );
}

function ErrorState({ msg }) {
  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ fontSize: '0.82rem', color: '#8B3A3A', background: 'rgba(139,58,58,0.08)', padding: '1rem 1.5rem', borderRadius: 10, border: '1px solid rgba(139,58,58,0.15)' }}>
        ⚠️ Error: {msg}
      </div>
    </div>
  );
}
