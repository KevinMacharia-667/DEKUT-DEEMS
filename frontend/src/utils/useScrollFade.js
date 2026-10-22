import { useEffect, useRef, useState } from 'react';

/**
 * Tracks whether a horizontal scroller has hidden content on either side.
 * Returns [ref, className]: attach the ref to the scrolling element and add the
 * className ('fade-left' / 'fade-right') so CSS can fade the edge that hides
 * more content, hinting on phones that the row scrolls.
 */
export function useScrollFade() {
  const ref = useRef(null);
  const [edges, setEdges] = useState({ left: false, right: false });

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;

    const update = () => {
      const maxScroll = el.scrollWidth - el.clientWidth;
      const left = el.scrollLeft > 2;
      const right = el.scrollLeft < maxScroll - 2;
      setEdges((prev) => (prev.left === left && prev.right === right ? prev : { left, right }));
    };

    update();
    el.addEventListener('scroll', update, { passive: true });
    const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(update) : null;
    observer?.observe(el);
    if (el.firstElementChild) observer?.observe(el.firstElementChild);
    return () => {
      el.removeEventListener('scroll', update);
      observer?.disconnect();
    };
  }, []);

  const className = [edges.left && 'fade-left', edges.right && 'fade-right'].filter(Boolean).join(' ');
  return [ref, className];
}

/** Scroll the selected item of a horizontal scroller into view without moving the page. */
export function scrollSelectedIntoView(container, selector) {
  const item = container?.querySelector(selector);
  if (!item) return;
  const reducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Position of the item inside the scroller's content, then centre it
  const itemLeft =
    item.getBoundingClientRect().left - container.getBoundingClientRect().left + container.scrollLeft;
  const target = itemLeft - (container.clientWidth - item.offsetWidth) / 2;
  container.scrollTo({ left: Math.max(0, target), behavior: reducedMotion ? 'auto' : 'smooth' });
}
