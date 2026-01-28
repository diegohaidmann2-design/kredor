import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import AssinaturaWrapper from './AssinaturaWrapper';
import { SidebarProvider, useSidebar } from '../context/SidebarContext';

const pageVariants = {
  initial: {
    opacity: 0,
    y: 10,
  },
  enter: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: [0.25, 0.46, 0.45, 0.94],
    },
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: {
      duration: 0.2,
    },
  },
};

const LayoutContent = ({ children }) => {
  const { isOpen } = useSidebar();
  const location = useLocation();
  
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      {/* Main content area - responsivo */}
      <main className={`min-h-screen transition-all duration-300 
        pt-16 lg:pt-0 
        px-0
        ${isOpen ? 'lg:ml-64' : 'lg:ml-20'}
      `}>
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            variants={pageVariants}
            initial="initial"
            animate="enter"
            exit="exit"
            className="w-full max-w-full overflow-x-hidden"
          >
            <AssinaturaWrapper>
              {children}
            </AssinaturaWrapper>
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
};

const Layout = ({ children }) => {
  return (
    <SidebarProvider>
      <LayoutContent>{children}</LayoutContent>
    </SidebarProvider>
  );
};

export default Layout;
