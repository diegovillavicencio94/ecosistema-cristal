import React from 'react';
import { motion } from 'framer-motion';

const STATS = [
  { value: '600.000M€', label: 'Gasto público anual en España' },
  { value: '309', label: 'Fragmentos indexados' },
  { value: '3', label: 'Documentos oficiales' },
];

export default function WelcomeScreen() {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: '3rem 2rem', gap: '2.5rem',
    }}>
      {/* Crystal icon */}
      <motion.div
        animate={{ rotate: [0, 5, -5, 0], scale: [1, 1.04, 0.97, 1] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          width: 72, height: 72, borderRadius: '50%',
          background: 'linear-gradient(135deg, rgba(232,168,56,0.5), rgba(59,107,158,0.4), rgba(255,255,255,0.6))',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(255,255,255,0.8)',
          boxShadow: '0 8px 32px rgba(232,168,56,0.2), inset 0 1px 0 rgba(255,255,255,0.9)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '1.8rem',
        }}
      >
        ◇
      </motion.div>

      {/* Title */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.6 }}
        style={{ textAlign: 'center' }}
      >
        <h2 style={{
          fontFamily: 'var(--serif)',
          fontSize: '2rem', fontWeight: 400,
          color: 'var(--text-primary)',
          lineHeight: 1.2, marginBottom: '0.65rem',
        }}>
          El Guía Experto
        </h2>
        <p style={{
          fontSize: '0.88rem', color: 'var(--text-secondary)',
          lineHeight: 1.65, maxWidth: 400, margin: '0 auto',
        }}>
          Pregunta sobre los presupuestos de la Comunidad de Madrid en lenguaje natural.
          Respondo con fuentes citadas de documentos oficiales.
        </p>
      </motion.div>

      {/* Stats row */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.6 }}
        style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}
      >
        {STATS.map((s, i) => (
          <div key={i} style={{
            background: 'rgba(255,255,255,0.45)',
            backdropFilter: 'blur(16px)',
            border: '1px solid rgba(255,255,255,0.7)',
            borderRadius: 14,
            padding: '0.85rem 1.25rem',
            textAlign: 'center',
            boxShadow: '0 4px 16px rgba(120,100,60,0.06)',
            minWidth: 110,
          }}>
            <div style={{ fontFamily: 'var(--serif)', fontSize: '1.3rem', fontWeight: 500, color: 'var(--blue)' }}>{s.value}</div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', marginTop: '0.2rem', lineHeight: 1.4 }}>{s.label}</div>
          </div>
        ))}
      </motion.div>

      {/* Hint */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5, duration: 0.8 }}
        style={{
          fontSize: '0.78rem', color: 'var(--text-tertiary)',
          display: 'flex', alignItems: 'center', gap: '0.4rem',
        }}
      >
        <span style={{ opacity: 0.5 }}>↙</span>
        Usa las preguntas sugeridas del panel izquierdo para empezar
      </motion.div>
    </div>
  );
}
