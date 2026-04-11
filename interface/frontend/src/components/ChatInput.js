import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';

export default function ChatInput({ onSubmit, disabled }) {
  const [value, setValue] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
  };

  const handleChange = (e) => {
    setValue(e.target.value);
    const el = textareaRef.current;
    if (el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 160) + 'px'; }
  };

  const isEmpty = !value.trim();

  return (
    <div style={{
      padding:'0.85rem 1.5rem 1.35rem',
      background:'linear-gradient(to top, rgba(242,239,232,0.97) 65%, transparent)',
      flexShrink:0,
    }}>
      <motion.div
        style={{
          display:'flex', alignItems:'flex-end', gap:'0.65rem',
          background:'rgba(255,255,255,0.65)',
          backdropFilter:'blur(28px) saturate(180%)',
          WebkitBackdropFilter:'blur(28px) saturate(180%)',
          border:'1px solid rgba(255,255,255,0.82)',
          borderRadius:20, padding:'0.7rem 0.7rem 0.7rem 1.2rem',
          boxShadow:'0 8px 32px rgba(120,100,60,0.1), inset 0 1px 0 rgba(255,255,255,0.95)',
          transition:'box-shadow 0.2s, border-color 0.2s',
        }}
        whileFocusWithin={{
          boxShadow:'0 8px 32px rgba(120,100,60,0.1), 0 0 0 2px rgba(232,168,56,0.3), inset 0 1px 0 rgba(255,255,255,0.95)',
          borderColor:'rgba(232,168,56,0.45)',
        }}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={disabled ? 'Consultando documentos…' : 'Pregunta sobre los presupuestos de Madrid…'}
          rows={1}
          style={{
            flex:1, background:'transparent', border:'none', outline:'none',
            resize:'none', fontFamily:'var(--sans)', fontSize:'0.9rem',
            color:'var(--text-primary)', lineHeight:1.6, maxHeight:160,
            overflowY:'auto', padding:'0.15rem 0',
            opacity: disabled ? 0.6 : 1,
          }}
        />
        <motion.button
          whileHover={{ scale: (disabled || isEmpty) ? 1 : 1.08 }}
          whileTap={{ scale: (disabled || isEmpty) ? 1 : 0.92 }}
          onClick={handleSubmit}
          disabled={disabled || isEmpty}
          style={{
            width:38, height:38, borderRadius:'50%', flexShrink:0,
            background: (disabled || isEmpty)
              ? 'rgba(180,170,160,0.28)'
              : 'linear-gradient(135deg, rgba(232,168,56,0.9), rgba(59,107,158,0.8))',
            border:'1px solid rgba(255,255,255,0.65)',
            cursor: (disabled || isEmpty) ? 'default' : 'pointer',
            display:'flex', alignItems:'center', justifyContent:'center',
            color: (disabled || isEmpty) ? 'rgba(150,140,130,0.6)' : 'white',
            fontSize:'1.1rem',
            boxShadow: (disabled || isEmpty) ? 'none' : '0 2px 12px rgba(232,168,56,0.35)',
            transition:'all 0.2s',
          }}
        >
          {disabled
            ? <motion.span animate={{ rotate:360 }} transition={{ duration:1.2, repeat:Infinity, ease:'linear' }}>◌</motion.span>
            : '↑'
          }
        </motion.button>
      </motion.div>
      <div style={{ textAlign:'center', marginTop:'0.45rem', fontSize:'0.63rem', color:'var(--text-tertiary)' }}>
        Enter para enviar · Shift+Enter para nueva línea
      </div>
    </div>
  );
}
