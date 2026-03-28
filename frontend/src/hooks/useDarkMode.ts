import { useState, useEffect } from 'react';

function getIsDarkMode() {
  return typeof document !== 'undefined' && document.documentElement.classList.contains('dark');
}

export function useDarkMode() {
  const [isDark, setIsDark] = useState(getIsDarkMode);

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setIsDark(getIsDarkMode());
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  return isDark;
}
