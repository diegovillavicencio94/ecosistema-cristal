import React from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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

export function AssistantMessage({ content, fuentes, onFuenteClick }) {
  // Strip inline source lines that llm.py sometimes appends
  // (lines starting with 📄 Fuente: or "Fuente:")
  const cleanContent = content
    .split('\n')
    .filter(line => !/^(📄\s*)?Fuente:/i.test(line.trim()))
    .join('\n')
    .trim();

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
          {/* Markdown content */}
          <div className="markdown-body" style={{ fontSize:'0.9rem', color:'var(--text-primary)', lineHeight:1.72 }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{cleanContent}</ReactMarkdown>
          </div>

          {/* Source capsules */}
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

// Animated typing dots
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
