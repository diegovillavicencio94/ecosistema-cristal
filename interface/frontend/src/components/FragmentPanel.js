import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function scoreColor(score) {
  if (score >= 0.75) return '#2E7D5A';
  if (score >= 0.55) return '#B07D2A';
  return '#8B3A3A';
}

// Convierte texto pipe-separated a tabla HTML
function PipeTable({ text }) {
  const lines = text.trim().split('\n').filter(l => l.includes('|'));
  if (lines.length < 2) return <pre style={{ fontSize:'0.78rem', whiteSpace:'pre-wrap', wordBreak:'break-word', lineHeight:1.6 }}>{text}</pre>;

  const parseRow = line => line.split('|').map(c => c.trim()).filter((_, i, arr) => !(i === 0 && arr[0] === '') && !(i === arr.length-1 && arr[arr.length-1] === ''));

  const headers = parseRow(lines[0]);
  const rows = lines.slice(1).map(parseRow);

  return (
    <div style={{ overflowX:'auto', marginTop:'0.5rem' }}>
      <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'0.75rem', fontFamily:'var(--sans)' }}>
        <thead>
          <tr>
            {headers.map((h,i) => (
              <th key={i} style={{
                padding:'0.4rem 0.6rem', textAlign:'left', fontWeight:500,
                background:'rgba(59,107,158,0.08)', borderBottom:'1px solid rgba(59,107,158,0.15)',
                color:'var(--blue)', whiteSpace:'nowrap',
              }}>{h || '—'}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row,i) => (
            <tr key={i} style={{ background: i%2===0 ? 'transparent' : 'rgba(0,0,0,0.02)' }}>
              {row.map((cell,j) => (
                <td key={j} style={{
                  padding:'0.35rem 0.6rem', borderBottom:'1px solid rgba(0,0,0,0.05)',
                  color:'var(--text-primary)', lineHeight:1.45,
                }}>{cell || '—'}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FragmentCard({ chunk, index, isTable }) {
  const score = chunk.score ?? 0;
  const color = scoreColor(score);

  return (
    <motion.div
      initial={{ opacity:0, y:16 }}
      animate={{ opacity:1, y:0 }}
      transition={{ delay: index * 0.07, duration:0.4, ease:[0.22,1,0.36,1] }}
      style={{
        background:'rgba(255,255,255,0.62)', backdropFilter:'blur(16px)',
        border:'1px solid rgba(255,255,255,0.75)', borderRadius:14,
        padding:'1rem 1.15rem',
        boxShadow:'0 2px 12px rgba(120,100,60,0.06)',
      }}
    >
      {/* Header row */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'0.55rem', gap:'0.5rem', flexWrap:'wrap' }}>
        <div style={{ fontSize:'0.71rem', color:'var(--text-secondary)', fontWeight:500, lineHeight:1.4 }}>
          Fragmento {index+1} · {chunk.source?.replace('.pdf','').replace(/_/g,' ')} · pág. {chunk.page}
        </div>

        {/* Score tag — solo si score > 0 (chunks de búsqueda semántica) */}
        {score > 0 && (
          <div style={{ display:'flex', alignItems:'center', gap:'0.3rem',
            background:`${color}14`, border:`1px solid ${color}33`,
            borderRadius:20, padding:'0.12rem 0.55rem', flexShrink:0 }}>
            <div style={{ width:5, height:5, borderRadius:'50%', background:color, boxShadow:`0 0 4px ${color}` }} />
            <span style={{ fontSize:'0.67rem', color, fontWeight:600 }}>score {score}</span>
          </div>
        )}
      </div>

      {/* Badges */}
      <div style={{ display:'flex', gap:'0.35rem', marginBottom:'0.65rem', flexWrap:'wrap' }}>
        <span style={{
          fontSize:'0.64rem', padding:'0.12rem 0.5rem',
          background: isTable ? 'rgba(59,107,158,0.1)' : 'rgba(232,168,56,0.12)',
          border:`1px solid ${isTable ? 'rgba(59,107,158,0.2)' : 'rgba(232,168,56,0.25)'}`,
          borderRadius:20, color: isTable ? 'var(--blue)' : '#8B6A10', fontWeight:500,
        }}>
          {isTable ? '📊 tabla' : '📝 texto'}
        </span>
        {chunk.organismo && (
          <span style={{
            fontSize:'0.64rem', padding:'0.12rem 0.5rem',
            background:'rgba(0,0,0,0.04)', border:'1px solid rgba(0,0,0,0.08)',
            borderRadius:20, color:'var(--text-tertiary)',
          }}>{chunk.organismo}</span>
        )}
        {chunk.doc_type && (
          <span style={{
            fontSize:'0.64rem', padding:'0.12rem 0.5rem',
            background:'rgba(0,0,0,0.04)', border:'1px solid rgba(0,0,0,0.08)',
            borderRadius:20, color:'var(--text-tertiary)',
          }}>{chunk.doc_type}</span>
        )}
        {chunk.año && (
          <span style={{
            fontSize:'0.64rem', padding:'0.12rem 0.5rem',
            background:'rgba(0,0,0,0.04)', border:'1px solid rgba(0,0,0,0.08)',
            borderRadius:20, color:'var(--text-tertiary)',
          }}>{chunk.año}</span>
        )}
      </div>

      {/* Content — tabla o texto */}
      {isTable
        ? <PipeTable text={chunk.content} />
        : <p style={{ fontSize:'0.82rem', color:'var(--text-primary)', lineHeight:1.68, wordBreak:'break-word' }}>
            {chunk.content?.slice(0,380)}{chunk.content?.length > 380 ? '…' : ''}
          </p>
      }
    </motion.div>
  );
}

export default function FragmentPanel({ chunks, onClose }) {
  return (
    <AnimatePresence>
      {chunks && (
        <>
          <motion.div key="backdrop"
            initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }}
            onClick={onClose}
            style={{ position:'fixed', inset:0, zIndex:40,
              background:'rgba(20,20,30,0.15)', backdropFilter:'blur(5px)', WebkitBackdropFilter:'blur(5px)' }}
          />

          <motion.div key="panel"
            initial={{ x:'100%', opacity:0 }} animate={{ x:0, opacity:1 }} exit={{ x:'100%', opacity:0 }}
            transition={{ type:'spring', stiffness:320, damping:30 }}
            style={{
              position:'fixed', top:0, right:0, bottom:0, width:480, zIndex:50,
              display:'flex', flexDirection:'column',
              background:'rgba(247,244,239,0.88)',
              backdropFilter:'blur(40px) saturate(200%)', WebkitBackdropFilter:'blur(40px) saturate(200%)',
              borderLeft:'1px solid rgba(255,255,255,0.8)',
              boxShadow:'-8px 0 48px rgba(120,100,60,0.14)',
            }}
          >
            {/* Header */}
            <div style={{ padding:'1.75rem 1.75rem 1.1rem', borderBottom:'1px solid rgba(120,100,60,0.1)',
              display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
              <div>
                <h2 style={{ fontFamily:'var(--serif)', fontSize:'1.5rem', fontWeight:400, color:'var(--text-primary)', lineHeight:1.2 }}>
                  <span style={{ color:'var(--blue)' }}>Recovered</span> Fragments
                </h2>
                <p style={{ fontSize:'0.73rem', color:'var(--text-tertiary)', marginTop:'0.2rem' }}>
                  {chunks.length} fragmento{chunks.length!==1?'s':''} recuperado{chunks.length!==1?'s':''}
                </p>
              </div>
              <motion.button whileHover={{ scale:1.1 }} whileTap={{ scale:0.95 }} onClick={onClose}
                style={{ width:32, height:32, borderRadius:'50%', background:'rgba(0,0,0,0.05)',
                  border:'1px solid rgba(0,0,0,0.08)', cursor:'pointer', fontSize:'0.9rem',
                  color:'var(--text-secondary)', display:'flex', alignItems:'center', justifyContent:'center' }}>
                ✕
              </motion.button>
            </div>

            {/* Scrollable list */}
            <div style={{ flex:1, overflowY:'auto', padding:'1.1rem 1.5rem', display:'flex', flexDirection:'column', gap:'0.75rem' }}>
              {chunks.map((chunk, i) => (
                <FragmentCard key={chunk.chunk_id || i} chunk={chunk} index={i} isTable={chunk.type==='table'} />
              ))}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
