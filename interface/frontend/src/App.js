import React, { useState, useEffect, useRef, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import axios from 'axios';

import AnimatedBackground from './components/AnimatedBackground';
import Sidebar from './components/Sidebar';
import { UserMessage, AssistantMessage, TypingIndicator } from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import FragmentPanel from './components/FragmentPanel';
import WelcomeScreen from './components/WelcomeScreen';

import ArchivoModule from './modules/Archivo/ArchivoModule';
import MapaModule from './modules/Mapa/MapaModule';

const API_BASE = 'http://localhost:8000';
const STORAGE_KEY = 'ec_mensajes_v2';

function cargarHistorial() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

const TABS = [
  { id: 'chat',    label: 'El Guía',    icon: '◎' },
  { id: 'archivo', label: 'El Archivo', icon: '▤'  },
  { id: 'mapa',    label: 'El Mapa',    icon: '⬡'  },
];

export default function App() {
  const [tab, setTab] = useState('chat');
  const [mensajes, setMensajes] = useState(cargarHistorial);
  const [loading, setLoading] = useState(false);
  const [filtros, setFiltros] = useState({ año: null, tipo_doc: null, top_k: 5 });
  const [fragmentPanel, setFragmentPanel] = useState(null);
  const [puntosIndexados, setPuntosIndexados] = useState(null);
  const chatEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(mensajes)); }
    catch { /* quota exceeded */ }
  }, [mensajes]);

  useEffect(() => {
    axios.get(`${API_BASE}/status`).then(r => setPuntosIndexados(r.data.puntos)).catch(() => {});
  }, []);

  useEffect(() => {
    if (tab === 'chat' && chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [mensajes, loading, tab]);

  const enviarPregunta = useCallback(async (pregunta) => {
    if (!pregunta.trim() || loading) return;
    setTab('chat');
    setMensajes(prev => [...prev, { role: 'user', content: pregunta }]);
    setLoading(true);

    try {
      const { data } = await axios.post(`${API_BASE}/preguntar`, {
        pregunta,
        top_k: filtros.top_k,
        año: filtros.año,
        tipo_doc: filtros.tipo_doc,
      });
      setMensajes(prev => [...prev, {
        role: 'assistant',
        content: data.respuesta,
        fuentes: data.fuentes,
        chunks: data.chunks,
        sin_contexto: data.sin_contexto,
        datos_grafico: data.datos_grafico ?? null,  // ← nuevo
      }]);
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message;
      setMensajes(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ **Error al procesar la consulta**\n\n\`${detail}\`\n\nAsegúrate de que el backend está corriendo:\n\`uvicorn interface.api:app --reload --port 8000\``,
        fuentes: [], chunks: [], datos_grafico: null,
      }]);
    } finally {
      setLoading(false);
    }
  }, [loading, filtros]);

  const limpiar = () => {
    setMensajes([]);
    setFragmentPanel(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  const abrirFragmento = useCallback((chunk) => {
    setFragmentPanel([chunk]);
  }, []);

  return (
    <div style={{ position: 'fixed', inset: 0, display: 'flex', overflow: 'hidden' }}>
      <AnimatedBackground />

      {tab === 'chat' && (
        <Sidebar
          filtros={filtros}
          setFiltros={setFiltros}
          onEjemplo={enviarPregunta}
          onLimpiar={limpiar}
          puntosIndexados={puntosIndexados}
        />
      )}

      <main style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        position: 'relative', zIndex: 5, overflow: 'hidden',
      }}>
        {/* ── Navbar ── */}
        <nav style={{
          display: 'flex', alignItems: 'stretch',
          borderBottom: '1px solid rgba(255,255,255,0.45)',
          background: 'rgba(242,239,232,0.5)',
          backdropFilter: 'blur(12px)',
          flexShrink: 0,
          padding: '0 1.5rem',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center',
            paddingRight: '1.5rem',
            borderRight: '1px solid rgba(0,0,0,0.08)',
            marginRight: '1rem',
          }}>
            <span style={{
              fontFamily: 'var(--serif)', fontSize: '0.85rem',
              fontWeight: 500, color: 'var(--text-primary)',
              letterSpacing: '-0.01em', whiteSpace: 'nowrap',
            }}>
              Ecosistema de Cristal
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'stretch', gap: '0.1rem', flex: 1 }}>
            {TABS.map(t => (
              <TabButton
                key={t.id}
                active={tab === t.id}
                onClick={() => setTab(t.id)}
                icon={t.icon}
                label={t.label}
              />
            ))}
          </div>

          {puntosIndexados !== null && (
            <div style={{
              display: 'flex', alignItems: 'center',
              fontSize: '0.68rem', color: 'var(--text-tertiary)', gap: '0.3rem',
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4CAF50', display: 'inline-block' }} />
              {puntosIndexados} fragmentos
            </div>
          )}
        </nav>

        {/* ── Contenido por tab ── */}
        <AnimatePresence mode="wait">
          {tab === 'chat' && (
            <motion.div
              key="chat"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
            >
              <div ref={chatContainerRef} style={{ flex: 1, overflowY: 'auto', padding: '1.5rem 2rem 0' }}>
                <AnimatePresence initial={false}>
                  {mensajes.length === 0 && !loading
                    ? <WelcomeScreen key="welcome" />
                    : mensajes.map((msg, i) =>
                        msg.role === 'user'
                          ? <UserMessage key={i} content={msg.content} />
                          : <AssistantMessage
                              key={i}
                              content={msg.content}
                              fuentes={msg.fuentes}
                              datos_grafico={msg.datos_grafico}   // ← nuevo
                              onFuenteClick={() => msg.chunks?.length && setFragmentPanel(msg.chunks)}
                            />
                      )
                  }
                </AnimatePresence>
                <AnimatePresence>
                  {loading && <TypingIndicator key="typing" />}
                </AnimatePresence>
                <div ref={chatEndRef} style={{ height: '0.5rem' }} />
              </div>
              <ChatInput onSubmit={enviarPregunta} disabled={loading} />
            </motion.div>
          )}

          {tab === 'archivo' && (
            <motion.div
              key="archivo"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
            >
              <ArchivoModule apiBase={API_BASE} onChunkClick={abrirFragmento} />
            </motion.div>
          )}

          {tab === 'mapa' && (
            <motion.div
              key="mapa"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
            >
              <MapaModule apiBase={API_BASE} onChunkClick={abrirFragmento} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <FragmentPanel chunks={fragmentPanel} onClose={() => setFragmentPanel(null)} />
    </div>
  );
}

function TabButton({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: '0.4rem',
        padding: '0.75rem 1rem',
        background: 'transparent', border: 'none',
        borderBottom: active ? '2px solid var(--text-primary)' : '2px solid transparent',
        cursor: 'pointer', fontSize: '0.78rem',
        fontWeight: active ? 600 : 400,
        color: active ? 'var(--text-primary)' : 'var(--text-tertiary)',
        letterSpacing: '-0.01em', transition: 'all 0.15s ease', whiteSpace: 'nowrap',
      }}
    >
      <span style={{ fontSize: '0.9rem', lineHeight: 1 }}>{icon}</span>
      {label}
    </button>
  );
}

function FilterBadge({ children }) {
  return (
    <div style={{
      background: 'rgba(232,168,56,0.12)', border: '1px solid rgba(232,168,56,0.28)',
      borderRadius: 20, padding: '0.18rem 0.65rem',
      fontSize: '0.72rem', color: '#8B6A10', fontWeight: 500,
    }}>
      {children}
    </div>
  );
}
