import React, { useEffect } from 'react';

const SPHERES = [
  { size: 700, x: -15, y: -20, color: 'rgba(232,168,56,0.55)',  blur: 60, duration: 28, delay: 0   },
  { size: 600, x: 55,  y: 45,  color: 'rgba(80,130,210,0.45)',  blur: 55, duration: 34, delay: -8  },
  { size: 500, x: 20,  y: 65,  color: 'rgba(232,168,56,0.38)',  blur: 50, duration: 22, delay: -14 },
  { size: 420, x: 72,  y: -10, color: 'rgba(59,107,158,0.38)',  blur: 48, duration: 40, delay: -5  },
  { size: 280, x: 45,  y: 35,  color: 'rgba(255,190,60,0.30)',  blur: 40, duration: 18, delay: -20 },
];

let stylesInjected = false;
function injectStyles() {
  if (stylesInjected) return;
  stylesInjected = true;
  const css = SPHERES.map((_, i) => `
    @keyframes float${i} {
      0%   { transform: translate(0px, 0px) scale(1); }
      25%  { transform: translate(${18+i*5}px, ${-22+i*4}px) scale(1.04); }
      50%  { transform: translate(${-12+i*3}px, ${28+i*3}px) scale(0.96); }
      75%  { transform: translate(${22-i*4}px, ${10-i*5}px) scale(1.03); }
      100% { transform: translate(0px, 0px) scale(1); }
    }
  `).join('\n');
  const el = document.createElement('style');
  el.textContent = css;
  document.head.appendChild(el);
}

export default function AnimatedBackground() {
  useEffect(() => { injectStyles(); }, []);
  return (
    <div style={{ position:'fixed', inset:0, zIndex:0, overflow:'hidden',
      background:'linear-gradient(135deg,#F2EFE8 0%,#E8E3D8 45%,#EDE8DF 100%)' }}>

      {SPHERES.map((s,i) => (
        <div key={i} style={{
          position:'absolute', width:s.size, height:s.size,
          left:`${s.x}%`, top:`${s.y}%`, borderRadius:'50%',
          background:`radial-gradient(circle at 38% 32%, ${s.color} 0%, ${s.color.replace(/[\d.]+\)$/,'0)')} 68%)`,
          filter:`blur(${s.blur}px)`,
          animation:`float${i} ${s.duration}s ease-in-out ${s.delay}s infinite`,
          zIndex:1, willChange:'transform', pointerEvents:'none',
        }} />
      ))}

      {/* Grid */}
      <div style={{ position:'absolute', inset:0, zIndex:2, pointerEvents:'none',
        backgroundImage:`linear-gradient(rgba(59,107,158,0.055) 1px,transparent 1px),linear-gradient(90deg,rgba(59,107,158,0.055) 1px,transparent 1px)`,
        backgroundSize:'48px 48px' }} />

      {/* Grain */}
      <div style={{ position:'absolute', inset:0, zIndex:3, opacity:0.04, pointerEvents:'none',
        backgroundImage:`url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
        backgroundSize:'128px 128px' }} />
    </div>
  );
}
