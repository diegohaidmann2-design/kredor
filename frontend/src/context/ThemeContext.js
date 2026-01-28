import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    // Verificar localStorage ou preferência do sistema
    const saved = localStorage.getItem('sgej-theme');
    if (saved) return saved;
    // Default: dark
    return 'dark';
  });

  useEffect(() => {
    const root = document.documentElement;
    
    // Remove ambas as classes primeiro
    root.classList.remove('dark', 'light');
    
    // Adiciona a classe do tema atual
    root.classList.add(theme);
    
    // Salva no localStorage
    localStorage.setItem('sgej-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const setDarkTheme = () => setTheme('dark');
  const setLightTheme = () => setTheme('light');

  return (
    <ThemeContext.Provider value={{ 
      theme, 
      toggleTheme, 
      setDarkTheme, 
      setLightTheme,
      isDark: theme === 'dark',
      isLight: theme === 'light'
    }}>
      {children}
    </ThemeContext.Provider>
  );
};

export default ThemeContext;
