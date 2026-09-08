import React, { createContext, useContext, useState, useEffect } from 'react';

const SidebarContext = createContext();

const SIDEBAR_OPEN_KEY = 'gestorcred_sidebar_open';

export const useSidebar = () => {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar deve ser usado dentro de um SidebarProvider');
  }
  return context;
};

export const SidebarProvider = ({ children }) => {
  // Persistimos o estado aberto/recolhido para sobreviver a remontagens do Layout
  // (cada página monta seu próprio Layout, então sem isso o estado resetaria a cada navegação).
  const [isOpen, setIsOpen] = useState(() => {
    try {
      const saved = localStorage.getItem(SIDEBAR_OPEN_KEY);
      return saved === null ? true : saved === 'true';
    } catch (e) {
      return true;
    }
  });
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_OPEN_KEY, String(isOpen));
    } catch (e) { /* noop */ }
  }, [isOpen]);

  const toggleSidebar = () => setIsOpen(!isOpen);
  const toggleMobile = () => setIsMobileOpen(!isMobileOpen);
  const closeMobile = () => setIsMobileOpen(false);

  return (
    <SidebarContext.Provider value={{
      isOpen,
      setIsOpen,
      isMobileOpen,
      setIsMobileOpen,
      toggleSidebar,
      toggleMobile,
      closeMobile
    }}>
      {children}
    </SidebarContext.Provider>
  );
};

export default SidebarContext;
