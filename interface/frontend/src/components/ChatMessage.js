import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  BarChart, Bar, PieChart, Pie, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  Cell, ResponsiveContainer,
} from 'recharts';

// ─── Paleta de colores para gráficos ─────────────────────────────────────────
const COLORES_GRAFICO = [
  '#3B6B9E', '#C8882A', '#4A9068', '#8B3A8B', '#C84444',
  '#2A8888', '#9E7A3B', '#6B3B9E', '#9E3B6B', '#4A6890',
];

// ─── Tooltip personalizado ────────────────────────────────────────────────────
function TooltipCustom({ active, payload, label, unidad }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(247,244,239,0.97)',
      backdropFilter: 'blur(16px)',
      border: '1px solid rgba(255,255,255,0.85)',
      borderRadius: 10, padding: '0.65rem 0.9rem',
      boxShadow: '0 8px 24px rgba(0,0,0,0.10)',
      fontSize: '0.75rem',
    }}>
      <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.3rem' }}>{label}</div>
      {payload.map((entry, i) => (
        <div key={i} style={{ color: entry.color, display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
          <span style={{ fontWeight: 500 }}>{entry.name || 'valor'}:</span>
          <span>{entry.value?.toLocaleString('es-ES')} {unidad}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Gráfico principal ────────────────────────────────────────────────────────
function GraficoRecharts({ datos_grafico }) {
  if (!datos_grafico) return null;

  const { tipo, titulo, unidad = '', comparativo, datos, datos_comparativo, etiqueta_a, etiqueta_b } = datos_grafico;

  // Altura adaptada al número de categorías
  const items = comparativo ? datos_comparativo : datos;
  const altura = Math.max(240, Math.min(380, (items?.length || 5) * 36));

  const tooltipProps = {
    content: <TooltipCustom unidad={unidad} />,
    cursor: { fill: 'rgba(59,107,158,0.06)' },
  };

  const ejeStyle = {
    fontSize: '0.68rem',
    fill: 'var(--text-tertiary)',
    fontFamily: 'var(--sans)',
  };

  // ── BAR comparativo (2 series) ───────────────────────────────────────────
  if (tipo === 'bar' && comparativo && datos_comparativo) {
    return (
      <ResponsiveContainer width="100%" height={altura}>
        <BarChart data={datos_comparativo} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
          <XAxis dataKey="nombre" tick={ejeStyle} tickLine={false} axisLine={false} />
          <YAxis tick={ejeStyle} tickLine={false} axisLine={false}
            tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
          <Tooltip {...tooltipProps} />
          <Legend wrapperStyle={{ fontSize: '0.72rem', paddingTop: '0.5rem' }} />
          <Bar dataKey="valor_a" name={etiqueta_a || 'Serie A'} fill={COLORES_GRAFICO[0]}
            radius={[4,4,0,0]} maxBarSize={40} />
          <Bar dataKey="valor_b" name={etiqueta_b || 'Serie B'} fill={COLORES_GRAFICO[1]}
            radius={[4,4,0,0]} maxBarSize={40} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // ── BAR simple ───────────────────────────────────────────────────────────
  if (tipo === 'bar' && datos) {
    return (
      <ResponsiveContainer width="100%" height={altura}>
        <BarChart data={datos} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
          <XAxis dataKey="nombre" tick={ejeStyle} tickLine={false} axisLine={false} />
          <YAxis tick={ejeStyle} tickLine={false} axisLine={false}
            tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
          <Tooltip {...tooltipProps} />
          <Bar dataKey="valor" name={unidad} radius={[4,4,0,0]} maxBarSize={48}>
            {datos.map((_, i) => (
              <Cell key={i} fill={COLORES_GRAFICO[i % COLORES_GRAFICO.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // ── PIE ──────────────────────────────────────────────────────────────────
  if (tipo === 'pie' && datos) {
    const total = datos.reduce((s, d) => s + (d.valor || 0), 0);
    return (
      <ResponsiveContainer width="100%" height={Math.max(260, altura)}>
        <PieChart>
          <Pie
            data={datos}
            dataKey="valor"
            nameKey="nombre"
            cx="50%" cy="50%"
            outerRadius="72%"
            innerRadius="38%"
            paddingAngle={2}
            label={({ nombre, valor }) =>
              `${nombre}: ${((valor / total) * 100).toFixed(1)}%`
            }
            labelLine={false}
          >
            {datos.map((_, i) => (
              <Cell key={i} fill={COLORES_GRAFICO[i % COLORES_GRAFICO.length]} />
            ))}
          </Pie>
          <Tooltip content={<TooltipCustom unidad={unidad} />} />
          <Legend wrapperStyle={{ fontSize: '0.70rem' }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  // ── LINE ─────────────────────────────────────────────────────────────────
  if (tipo === 'line' && datos) {
    return (
      <ResponsiveContainer width="100%" height={altura}>
        <LineChart data={datos} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
          <XAxis dataKey="nombre" tick={ejeStyle} tickLine={false} axisLine={false} />
          <YAxis tick={ejeStyle} tickLine={false} axisLine={false} />
          <Tooltip content={<TooltipCustom unidad={unidad} />} />
          <Line type="monotone" dataKey="valor" stroke={COLORES_GRAFICO[0]}
            strokeWidth={2} dot={{ r: 4, fill: COLORES_GRAFICO[0] }} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  return null;
}

// ─── UserMessage ──────────────────────────────────────────────────────────────
export function UserMessage({ content }) {
  return (
    <motion.div
      initial={{ opacity:0, y:16, scale:0.98 }}
      animate={{ opacity:1, y:0, scale:1 }}
      transition={{ duration:0.35, ease:[0.22,1,0.36,1] }}
      style={{ display:'flex', justifyContent:'flex-end', marginBottom:'1rem' }}
    >
      <div style={{
        maxWidth:'72%',
        background:'linear-gradient(135deg, rgba(59,107,158,0.85), rgba(40,80,130,0.9))',
        backdropFilter:'blur(16px)',
        border:'1px solid rgba(100,150,220,0.3)',
        borderRadius:'18px 18px 4px 18px',
        padding:'0.85rem 1.15rem',
        fontSize:'0.9rem', lineHeight:1.65,
        color:'rgba(255,255,255,0.95)',
        boxShadow:'0 4px 20px rgba(59,107,158,0.25)',
        fontFamily:'var(--sans)',
      }}>
        {content}
      </div>
    </motion.div>
  );
}

// ─── AssistantMessage ─────────────────────────────────────────────────────────
export function AssistantMessage({ content, fuentes, datos_grafico, onFuenteClick }) {
  const [graficoVisible, setGraficoVisible] = useState(true);

  const cleanContent = content
    .split('\n')
    .filter(line => !/^(📄\s*)?Fuente:/i.test(line.trim()))
    .join('\n')
    .trim();

  const hayGrafico = datos_grafico && (
    datos_grafico.datos?.length > 0 ||
    datos_grafico.datos_comparativo?.length > 0
  );

  return (
    <motion.div
      initial={{ opacity:0, y:24, scale:0.97 }}
      animate={{ opacity:1, y:0, scale:1 }}
      transition={{ duration:0.5, ease:[0.22,1,0.36,1] }}
      style={{ display:'flex', gap:'0.85rem', marginBottom:'1.25rem', alignItems:'flex-start' }}
    >
      {/* Avatar */}
      <div style={{
        width:36, height:36, borderRadius:'50%', flexShrink:0, marginTop:2,
        background:'linear-gradient(135deg, rgba(232,168,56,0.65), rgba(59,107,158,0.5))',
        backdropFilter:'blur(8px)',
        border:'1px solid rgba(255,255,255,0.75)',
        boxShadow:'0 2px 12px rgba(232,168,56,0.22)',
        display:'flex', alignItems:'center', justifyContent:'center',
        fontSize:'0.8rem',
      }}>◇</div>

      <div style={{ flex:1, minWidth:0 }}>
        <div style={{
          background:'rgba(255,255,255,0.52)',
          backdropFilter:'blur(28px) saturate(180%)',
          WebkitBackdropFilter:'blur(28px) saturate(180%)',
          border:'1px solid rgba(255,255,255,0.75)',
          borderRadius:'4px 18px 18px 18px',
          padding:'1.15rem 1.35rem',
          boxShadow:'0 8px 32px rgba(120,100,60,0.08), inset 0 1px 0 rgba(255,255,255,0.85)',
        }}>
          {/* Texto de respuesta */}
          <div className="markdown-body" style={{ fontSize:'0.9rem', color:'var(--text-primary)', lineHeight:1.72 }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{cleanContent}</ReactMarkdown>
          </div>

          {/* Gráfico */}
          {hayGrafico && (
            <div style={{ marginTop:'1rem' }}>
              {/* Header del gráfico */}
              <div style={{
                display:'flex', alignItems:'center', justifyContent:'space-between',
                marginBottom: graficoVisible ? '0.75rem' : 0,
              }}>
                <div style={{ display:'flex', alignItems:'center', gap:'0.4rem' }}>
                  <span style={{ fontSize:'0.72rem' }}>📊</span>
                  <span style={{ fontSize:'0.72rem', fontWeight:600, color:'var(--text-secondary)', letterSpacing:'0.02em' }}>
                    {datos_grafico.titulo}
                  </span>
                  {datos_grafico.unidad && (
                    <span style={{ fontSize:'0.65rem', color:'var(--text-tertiary)' }}>
                      ({datos_grafico.unidad})
                    </span>
                  )}
                </div>
                <motion.button
                  whileHover={{ scale:1.03 }}
                  whileTap={{ scale:0.97 }}
                  onClick={() => setGraficoVisible(v => !v)}
                  style={{
                    background:'rgba(0,0,0,0.04)',
                    border:'1px solid rgba(0,0,0,0.08)',
                    borderRadius:20, padding:'0.18rem 0.65rem',
                    fontSize:'0.65rem', color:'var(--text-tertiary)',
                    cursor:'pointer', fontFamily:'var(--sans)',
                  }}
                >
                  {graficoVisible ? 'Ocultar gráfico' : 'Ver gráfico'}
                </motion.button>
              </div>

              {/* Gráfico animado */}
              <AnimatePresence>
                {graficoVisible && (
                  <motion.div
                    initial={{ opacity:0, height:0 }}
                    animate={{ opacity:1, height:'auto' }}
                    exit={{ opacity:0, height:0 }}
                    transition={{ duration:0.3, ease:[0.22,1,0.36,1] }}
                    style={{
                      overflow:'hidden',
                      background:'rgba(255,255,255,0.4)',
                      borderRadius:12,
                      padding:'1rem 0.5rem 0.5rem',
                      border:'1px solid rgba(255,255,255,0.7)',
                    }}
                  >
                    <GraficoRecharts datos_grafico={datos_grafico} />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Fuentes */}
          {fuentes && fuentes.length > 0 && (
            <div style={{ marginTop:'1rem', paddingTop:'0.85rem', borderTop:'1px solid rgba(120,100,60,0.1)' }}>
              <div style={{ fontSize:'0.64rem', textTransform:'uppercase', letterSpacing:'0.12em',
                color:'var(--text-tertiary)', marginBottom:'0.5rem', fontWeight:500 }}>
                Fuentes consultadas
              </div>
              <div style={{ display:'flex', flexWrap:'wrap', gap:'0.4rem' }}>
                {fuentes.map((f, i) => (
                  <SourceCapsule key={i} fuente={f} onClick={onFuenteClick} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ─── SourceCapsule ────────────────────────────────────────────────────────────
function SourceCapsule({ fuente, onClick }) {
  const nombre = (fuente.source || '').replace('.pdf','').replace(/_/g,' ');
  const corto = nombre.length > 26 ? nombre.slice(0,26) + '…' : nombre;

  return (
    <motion.button
      whileHover={{
        scale:1.03,
        boxShadow:'0 0 0 2px rgba(232,168,56,0.4), 0 4px 12px rgba(232,168,56,0.18)',
        borderColor:'rgba(232,168,56,0.55)',
      }}
      whileTap={{ scale:0.97 }}
      onClick={onClick}
      title={fuente.source}
      style={{
        background:'rgba(255,255,255,0.6)',
        border:'1px solid rgba(255,255,255,0.75)',
        borderRadius:20, padding:'0.28rem 0.75rem',
        fontSize:'0.72rem', color:'var(--blue)',
        cursor:'pointer', display:'flex', alignItems:'center', gap:'0.35rem',
        backdropFilter:'blur(8px)', fontFamily:'var(--sans)', fontWeight:400,
        transition:'border-color 0.2s', lineHeight:1,
      }}
    >
      <span style={{ fontSize:'0.62rem', opacity:0.65 }}>📄</span>
      <span>{corto}</span>
      <span style={{ color:'var(--text-tertiary)', flexShrink:0 }}>· p.{fuente.page}</span>
    </motion.button>
  );
}

// ─── TypingIndicator ──────────────────────────────────────────────────────────
export function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity:0, y:12 }}
      animate={{ opacity:1, y:0 }}
      exit={{ opacity:0, y:-8 }}
      transition={{ duration:0.3 }}
      style={{ display:'flex', gap:'0.85rem', alignItems:'flex-start', marginBottom:'1rem' }}
    >
      <div style={{
        width:36, height:36, borderRadius:'50%', flexShrink:0,
        background:'linear-gradient(135deg, rgba(232,168,56,0.65), rgba(59,107,158,0.5))',
        border:'1px solid rgba(255,255,255,0.75)',
        display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.8rem',
      }}>◇</div>

      <div style={{
        background:'rgba(255,255,255,0.52)', backdropFilter:'blur(28px)',
        border:'1px solid rgba(255,255,255,0.75)',
        borderRadius:'4px 18px 18px 18px', padding:'1rem 1.35rem',
        display:'flex', alignItems:'center', gap:'0.45rem',
        boxShadow:'0 8px 32px rgba(120,100,60,0.08)',
      }}>
        <span style={{ fontSize:'0.75rem', color:'var(--text-tertiary)', marginRight:'0.3rem', fontStyle:'italic' }}>
          Consultando documentos
        </span>
        {[0,1,2].map(i => (
          <motion.div key={i}
            animate={{ y:[0,-6,0], opacity:[0.4,1,0.4] }}
            transition={{ duration:0.9, repeat:Infinity, delay:i*0.18, ease:'easeInOut' }}
            style={{ width:6, height:6, borderRadius:'50%', background:'var(--amber)' }}
          />
        ))}
      </div>
    </motion.div>
  );
}
