import React, { useEffect, useRef, useState } from 'react';

/**
 * Anima um número de um valor anterior até o novo (ease-out cubic).
 * `format` recebe o número corrente e devolve a string exibida.
 */
const AnimatedNumber = ({ value = 0, duration = 900, format = (n) => n, className }) => {
  const [display, setDisplay] = useState(0);
  const state = useRef({ raf: 0, from: 0 });

  useEffect(() => {
    const from = state.current.from;
    const to = Number(value) || 0;
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const cur = from + (to - from) * eased;
      setDisplay(cur);
      if (t < 1) state.current.raf = requestAnimationFrame(tick);
      else state.current.from = to;
    };
    cancelAnimationFrame(state.current.raf);
    state.current.raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(state.current.raf);
  }, [value, duration]);

  return <span className={className}>{format(display)}</span>;
};

export default AnimatedNumber;
