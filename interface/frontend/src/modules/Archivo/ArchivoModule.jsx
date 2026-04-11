// interface/frontend/src/modules/Archivo/ArchivoModule.jsx

import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

// ─── Paleta por doc_type ──────────────────────────────────────────────────
const DOC_COLORS = {
  articulado: { bg: 'rgba(59,107,158,0.10)', border: 'rgba(59,107,158,0.22)', text: '#2B5F9E' },
  folleto:    { bg: 'rgba(232,168,56,0.10)', border: 'rgba(232,168,56,0.25)', text: '#8B6A10' },
  resumen:    { bg: 'rgba(80,140,100,0.10)', border: 'rgba(80,140,100,0.22)', text: '#2E7D5A' },
};
const fallbackColor = { bg: 'rgba(0,0,0,0.05)', border: 'rgba(0,0,0,0.10)', text: '#555' };

function docColor(type) { return DOC_COLORS[type] || fallbackColor; }

// ─── Badge inline ─────────────────────────────────────────────────────────
function Badge({ label, color }) {
  return (
    <span style={{
      fontSize: '0.63rem', fontWeight: 600, letterSpacing: '0.03em',
      padding: '0.12rem 0.5rem', borderRadius: 20,
      background: color.bg, border: `1px solid ${color.border}`,
      color: color.text, whiteSpace: 'nowrap',
    }}>{label}</span>
  );
}

// ─── Stat card (cabecera) ─────────────────────────────────────────────────
function StatCard({ label, value, sub }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        background: 'rgba(255,255,255,0.55)',
        backdropFilter: 'blur(14px)',
        border: '1px solid rgba(255,255,255,0.75)',
        borderRadius: 12,
        padding: '0.85rem 1.2rem',
        minWidth: 120,
      }}
    >
      <div style={{ fontSize: '1.5rem', fontFamily: 'var(--serif)', fontWeight: 400, color: 'var(--text-primary)', lineHeight: 1 }}>
        {value}
      </div>
      <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', marginTop: '0.25rem', fontWeight: 500 }}>
        {label}
      </div>
      {sub && <div style={{ fontSize: '0.62rem', color: 'var(--text-tertiary)', marginTop: '0.1rem' }}>{sub}</div>}
    </motion.div>
  );
}

// ─── Fila de tabla ────────────────────────────────────────────────────────
function ChunkRow({ chunk, index, onClick }) {
  const [hovered, setHovered] = useState(false);
  const dc = docColor(chunk.doc_type);
  const nombreCorto = chunk.source
    ?.replace('.pdf', '')
    .replace(/_/g, ' ')
    .replace(/\(\d+\)/, '')
    .trim()
    .slice(0, 38);

  return (
    <motion.tr
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: Math.min(index * 0.008, 0.3) }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => onClick(chunk)}
      style={{
        cursor: 'pointer',
        background: hovered ? 'rgba(59,107,158,0.06)' : index % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.015)',
        transition: 'background 0.12s ease',
        borderBottom: '1px solid rgba(0,0,0,0.05)',
      }}
    >
      {/* Nº */}
      <td style={{ padding: '0.5rem 0.75rem', fontSize: '0.67rem', color: 'var(--text-tertiary)', fontVariantNumeric: 'tabular-nums', width: 40 }}>
        {index + 1}
      </td>
      {/* Tipo contenido */}
      <td style={{ padding: '0.5rem 0.4rem', width: 60 }}>
        <span style={{ fontSize: '0.72rem' }}>{chunk.type === 'table' ? '📊' : '📝'}</span>
      </td>
      {/* Doc type */}
      <td style={{ padding: '0.5rem 0.4rem', width: 90 }}>
        <Badge label={chunk.doc_type || '—'} color={dc} />
      </td>
      {/* Año */}
      <td style={{ padding: '0.5rem 0.4rem', fontSize: '0.72rem', color: 'var(--text-secondary)', width: 50, fontVariantNumeric: 'tabular-nums' }}>
        {chunk.año || '—'}
      </td>
      {/* Fuente */}
      <td style={{ padding: '0.5rem 0.4rem', fontSize: '0.72rem', color: 'var(--text-secondary)', maxWidth: 180 }}>
        <span title={chunk.source}>{nombreCorto}</span>
      </td>
      {/* Pág */}
      <td style={{ padding: '0.5rem 0.4rem', fontSize: '0.72rem', color: 'var(--text-tertiary)', width: 40, fontVariantNumeric: 'tabular-nums' }}>
        {chunk.page || '—'}
      </td>
      {/* Preview */}
      <td style={{ padding: '0.5rem 0.75rem', fontSize: '0.72rem', color: hovered ? 'var(--text-primary)' : 'var(--text-secondary)', lineHeight: 1.4, transition: 'color 0.12s' }}>
        {chunk.content?.slice(0, 90)}{chunk.content?.length > 90 ? '…' : ''}
      </td>
    </motion.tr>
  );
}

// ─── Módulo principal ─────────────────────────────────────────────────────
export default function ArchivoModule({ apiBase, onChunkClick }) {
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filtros activos
  const [filtroDocType, setFiltroDocType] = useState('todos');
  const [filtroTipo, setFiltroTipo]       = useState('todos'); // text | table
  const [filtroAño, setFiltroAño]         = useState('todos');
  const [busqueda, setBusqueda]           = useState('');

  // Fetch al montar
  useEffect(() => {
    setLoading(true);
    axios.get(`${apiBase}/chunks`, { params: { limit: 500 } })
      .then(r => { setChunks(r.data); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [apiBase]);

  // Stats derivadas
  const stats = useMemo(() => {
    const total = chunks.length;
    const porTipo = chunks.reduce((acc, c) => {
      acc[c.doc_type] = (acc[c.doc_type] || 0) + 1; return acc;
    }, {});
    const tablas = chunks.filter(c => c.type === 'table').length;
    const años = [...new Set(chunks.map(c => c.año).filter(Boolean))].sort();
    return { total, porTipo, tablas, años };
  }, [chunks]);

  // Chunks filtrados
  const filtrados = useMemo(() => {
    return chunks.filter(c => {
      if (filtroDocType !== 'todos' && c.doc_type !== filtroDocType) return false;
      if (filtroTipo !== 'todos' && c.type !== filtroTipo) return false;
      if (filtroAño !== 'todos' && String(c.año) !== filtroAño) return false;
      if (busqueda.trim()) {
        const q = busqueda.toLowerCase();
        if (!c.content?.toLowerCase().includes(q) && !c.source?.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [chunks, filtroDocType, filtroTipo, filtroAño, busqueda]);

  // ── Render ──
  if (loading) return <LoadingState />;
  if (error)   return <ErrorState msg={error} />;

  const docTypes = ['todos', ...Object.keys(DOC_COLORS).filter(k => stats.porTipo[k])];
  const años     = ['todos', ...stats.años.map(String)];

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '1.25rem 1.75rem 0' }}>

      {/* ── Cabecera con título + stats ── */}
      <div style={{ marginBottom: '1rem', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.9rem' }}>
          <h1 style={{ fontFamily: 'var(--serif)', fontSize: '1.4rem', fontWeight: 400, color: 'var(--text-primary)', margin: 0 }}>
            El Archivo
          </h1>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
            Índice de fragmentos indexados en el sistema
          </span>
        </div>

        {/* Stat cards */}
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <StatCard label="fragmentos totales" value={stats.total} />
          {Object.entries(stats.porTipo).map(([tipo, n]) => (
            <StatCard
              key={tipo}
              label={tipo}
              value={n}
              sub={`${Math.round(n / stats.total * 100)}% del total`}
            />
          ))}
          <StatCard label="tablas" value={stats.tablas} sub={`${stats.total - stats.tablas} textos`} />
        </div>
      </div>

      {/* ── Barra de filtros ── */}
      <div style={{
        display: 'flex', gap: '0.6rem', alignItems: 'center',
        marginBottom: '0.75rem', flexShrink: 0, flexWrap: 'wrap',
      }}>
        {/* Búsqueda libre */}
        <input
          value={busqueda}
          onChange={e => setBusqueda(e.target.value)}
          placeholder="Buscar en contenido o fuente…"
          style={{
            flex: 1, minWidth: 200, maxWidth: 340,
            padding: '0.4rem 0.8rem',
            background: 'rgba(255,255,255,0.6)',
            border: '1px solid rgba(0,0,0,0.12)',
            borderRadius: 8, fontSize: '0.78rem',
            color: 'var(--text-primary)',
            outline: 'none',
            backdropFilter: 'blur(8px)',
          }}
        />

        <FilterSelect label="Tipo doc" value={filtroDocType} onChange={setFiltroDocType} options={docTypes} />
        <FilterSelect label="Contenido" value={filtroTipo} onChange={setFiltroTipo}
          options={['todos', 'text', 'table']}
          labels={{ todos: 'Todos', text: '📝 Texto', table: '📊 Tabla' }}
        />
        <FilterSelect label="Año" value={filtroAño} onChange={setFiltroAño} options={años} />

        {/* Contador resultados */}
        <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', marginLeft: 'auto' }}>
          {filtrados.length} resultado{filtrados.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* ── Tabla ── */}
      <div style={{
        flex: 1, overflowY: 'auto',
        background: 'rgba(255,255,255,0.45)',
        backdropFilter: 'blur(14px)',
        border: '1px solid rgba(255,255,255,0.7)',
        borderRadius: 14,
        marginBottom: '1.25rem',
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
          <thead>
            <tr style={{
              background: 'rgba(242,239,232,0.7)',
              position: 'sticky', top: 0, zIndex: 2,
              borderBottom: '1px solid rgba(0,0,0,0.08)',
            }}>
              {['#', '', 'Tipo', 'Año', 'Documento', 'Pág', 'Contenido'].map((h, i) => (
                <th key={i} style={{
                  padding: '0.55rem 0.75rem',
                  fontSize: '0.67rem', fontWeight: 600,
                  color: 'var(--text-tertiary)',
                  textAlign: 'left', letterSpacing: '0.04em',
                  textTransform: 'uppercase',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <AnimatePresence>
              {filtrados.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '0.82rem' }}>
                    Ningún fragmento coincide con los filtros
                  </td>
                </tr>
              ) : filtrados.map((chunk, i) => (
                <ChunkRow key={chunk.chunk_id} chunk={chunk} index={i} onClick={onChunkClick} />
              ))}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────
function FilterSelect({ value, onChange, options, labels = {} }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        padding: '0.4rem 0.65rem',
        background: 'rgba(255,255,255,0.6)',
        border: '1px solid rgba(0,0,0,0.12)',
        borderRadius: 8, fontSize: '0.75rem',
        color: 'var(--text-primary)', cursor: 'pointer',
        backdropFilter: 'blur(8px)',
        outline: 'none',
      }}
    >
      {options.map(o => (
        <option key={o} value={o}>{labels[o] || o}</option>
      ))}
    </select>
  );
}

function LoadingState() {
  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '0.75rem' }}>
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
        style={{ width: 28, height: 28, border: '2px solid rgba(59,107,158,0.15)', borderTop: '2px solid var(--blue)', borderRadius: '50%' }}
      />
      <span style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)' }}>Cargando fragmentos…</span>
    </div>
  );
}

function ErrorState({ msg }) {
  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ fontSize: '0.82rem', color: '#8B3A3A', background: 'rgba(139,58,58,0.08)', padding: '1rem 1.5rem', borderRadius: 10, border: '1px solid rgba(139,58,58,0.15)' }}>
        ⚠️ Error cargando chunks: {msg}
      </div>
    </div>
  );
}