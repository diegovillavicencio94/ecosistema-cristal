import React from 'react';
import { motion } from 'framer-motion';

const EJEMPLO_PREGUNTAS = [
  '¿Cuánto se gasta en sanidad en 2026?',
  '¿Qué es el capítulo 1 de gastos de personal?',
  '¿Cuáles son los ingresos totales previstos?',
  '¿Cuánto va a educación en Madrid?',
];

export default function Sidebar({ filtros, setFiltros, onEjemplo, onLimpiar, puntosIndexados }) {
  return (
    <motion.aside
      initial={{ x: -40, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      style={{
        width: 300,
        minWidth: 300,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        padding: '2rem 1.5rem',
        background: 'rgba(255,255,255,0.28)',
        backdropFilter: 'blur(28px) saturate(180%)',
        WebkitBackdropFilter: 'blur(28px) saturate(180%)',
        borderRight: '1px solid rgba(255,255,255,0.6)',
        boxShadow: 'inset -1px 0 0 rgba(120,100,60,0.06), 4px 0 24px rgba(0,0,0,0.04)',
        zIndex: 10,
        overflowY: 'auto',
        gap: '1.75rem',
      }}
    >
      {/* Logo / Brand */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: 'linear-gradient(135deg, rgba(232,168,56,0.7), rgba(59,107,158,0.5))',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255,255,255,0.7)',
            boxShadow: '0 2px 12px rgba(232,168,56,0.25)',
            flexShrink: 0,
          }} />
          <span style={{ fontFamily: 'var(--sans)', fontSize: '0.72rem', fontWeight: 500, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
            Crystal Ecosystem
          </span>
        </div>
        <h1 style={{
          fontFamily: 'var(--serif)',
          fontSize: '1.65rem',
          fontWeight: 400,
          lineHeight: 1.2,
          color: 'var(--text-primary)',
          letterSpacing: '-0.01em',
        }}>
          El Ecosistema<br />de Cristal
        </h1>
        <p style={{
          marginTop: '0.5rem',
          fontSize: '0.78rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.55,
          fontWeight: 300,
        }}>
          Plataforma de Transparencia Ciudadana impulsada por Inteligencia Artificial
        </p>
      </div>

      <Divider />

      {/* Filters */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <Label>Filtros de búsqueda</Label>

        <FilterGroup label="Año Presupuestario">
          <GlassSelect
            value={filtros.año ?? ''}
            onChange={e => setFiltros(f => ({ ...f, año: e.target.value ? parseInt(e.target.value) : null }))}
          >
            <option value="">Todos los años</option>
            <option value="2025">2025</option>
            <option value="2026">2026</option>
          </GlassSelect>
        </FilterGroup>

        <FilterGroup label="Tipo de Documento">
          <GlassSelect
            value={filtros.tipo_doc ?? ''}
            onChange={e => setFiltros(f => ({ ...f, tipo_doc: e.target.value || null }))}
          >
            <option value="">Todos los documentos</option>
            <option value="folleto">Folleto resumen</option>
            <option value="articulado">Articulado / Ley</option>
            <option value="memoria">Memoria</option>
          </GlassSelect>
        </FilterGroup>

        <FilterGroup label={`Fragmentos a recuperar — ${filtros.top_k}`}>
          <input
            type="range" min={1} max={10} value={filtros.top_k}
            onChange={e => setFiltros(f => ({ ...f, top_k: parseInt(e.target.value) }))}
            style={{ width: '100%', accentColor: 'var(--amber)', cursor: 'pointer' }}
          />
        </FilterGroup>
      </div>

      <Divider />

      {/* Suggested questions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <Label>Preguntas sugeridas</Label>
        {EJEMPLO_PREGUNTAS.map((q, i) => (
          <motion.button
            key={i}
            whileHover={{ scale: 1.01, backgroundColor: 'rgba(255,255,255,0.55)' }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onEjemplo(q)}
            style={{
              background: 'rgba(255,255,255,0.32)',
              border: '1px solid rgba(255,255,255,0.6)',
              borderRadius: 10,
              padding: '0.6rem 0.85rem',
              fontSize: '0.79rem',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              textAlign: 'left',
              lineHeight: 1.45,
              backdropFilter: 'blur(8px)',
              transition: 'background 0.2s',
              fontFamily: 'var(--sans)',
            }}
          >
            {q}
          </motion.button>
        ))}
      </div>

      <div style={{ flexGrow: 1 }} />

      {/* System info */}
      <div style={{
        fontSize: '0.7rem',
        color: 'var(--text-tertiary)',
        lineHeight: 1.7,
        padding: '0.75rem',
        background: 'rgba(255,255,255,0.25)',
        border: '1px solid rgba(255,255,255,0.5)',
        borderRadius: 10,
      }}>
        <div style={{ fontWeight: 500, marginBottom: '0.25rem', letterSpacing: '0.08em', textTransform: 'uppercase', fontSize: '0.65rem' }}>Sistema</div>
        LLM: Gemini 2.5 Flash<br />
        Embeddings: gemini-embedding-001<br />
        Vector DB: Qdrant · {puntosIndexados ?? '—'} puntos
      </div>

      {/* Clear button */}
      <motion.button
        whileHover={{ backgroundColor: 'rgba(220,60,60,0.08)', borderColor: 'rgba(220,60,60,0.25)' }}
        whileTap={{ scale: 0.97 }}
        onClick={onLimpiar}
        style={{
          background: 'rgba(255,255,255,0.3)',
          border: '1px solid rgba(200,180,160,0.4)',
          borderRadius: 10,
          padding: '0.65rem',
          fontSize: '0.8rem',
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.4rem',
          fontFamily: 'var(--sans)',
          transition: 'all 0.2s',
        }}
      >
        <span>🗑</span> Limpiar conversación
      </motion.button>
    </motion.aside>
  );
}

function Divider() {
  return <div style={{ height: 1, background: 'linear-gradient(90deg, transparent, rgba(120,100,60,0.15), transparent)' }} />;
}

function Label({ children }) {
  return (
    <div style={{ fontSize: '0.68rem', fontWeight: 500, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>
      {children}
    </div>
  );
}

function FilterGroup({ label, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
      <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 400 }}>{label}</label>
      {children}
    </div>
  );
}

function GlassSelect({ children, ...props }) {
  return (
    <select
      {...props}
      style={{
        width: '100%',
        padding: '0.55rem 0.85rem',
        background: 'rgba(255,255,255,0.45)',
        border: '1px solid rgba(255,255,255,0.65)',
        borderRadius: 9,
        fontSize: '0.82rem',
        color: 'var(--text-primary)',
        cursor: 'pointer',
        outline: 'none',
        fontFamily: 'var(--sans)',
        backdropFilter: 'blur(8px)',
        boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
        appearance: 'none',
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%236B6B70' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E")`,
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 0.85rem center',
        paddingRight: '2.2rem',
      }}
    >
      {children}
    </select>
  );
}
