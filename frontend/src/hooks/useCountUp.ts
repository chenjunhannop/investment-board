import { useEffect, useRef, useState } from 'react';

/**
 * Whether the user has requested reduced motion via OS/accessibility settings.
 * Returns false in non-browser environments (SSR safety).
 */
function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

/**
 * Animated numeric counter that tweens toward `value` using easeOutCubic.
 *
 * Respects `prefers-reduced-motion`: when the user requests reduced motion the
 * display value jumps straight to `value` without animating.
 *
 * @param value - target numeric value to count up/down to
 * @param duration - animation duration in ms (default 300)
 * @returns the animated display value
 */
export function useCountUp(value: number, duration = 300): number {
  const [display, setDisplay] = useState(value);
  const prevRef = useRef(value);
  useEffect(() => {
    if (prefersReducedMotion()) {
      setDisplay(value);
      prevRef.current = value;
      return;
    }
    const from = prevRef.current;
    if (from === value) {
      return;
    }
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min((t - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      setDisplay(from + (value - from) * eased);
      if (p < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        prevRef.current = value;
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return display;
}
