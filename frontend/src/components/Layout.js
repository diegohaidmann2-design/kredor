import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import AssinaturaWrapper from './AssinaturaWrapper';
import { SidebarProvider, useSidebar } from '../context/SidebarContext';
import { useAuth } from '../context/AuthContext';
import { ehMembro } from '../lib/permissoes';

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

// Membro criado sem nenhuma permissão marcada é o estado padrão logo depois do cadastro: ele
// entra, o menu tem quase nada e nenhuma tela explica o motivo. Sem este aviso, o silêncio
// parece defeito do sistema em vez de uma configuração que falta o dono fazer.
const AvisoSemPermissao = () => (
  <div
    className="mx-4 mt-4 rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm"
    data-testid="aviso-membro-sem-permissao"
  >
    <strong className="font-medium">Seu acesso ainda não foi liberado.</strong>{' '}
    Você entrou na conta, mas o dono ainda não escolheu o que você pode ver. Peça a ele para
    ajustar as suas permissões em Minha Equipe.
  </div>
);

const LayoutContent = ({ children }) => {
  const { isOpen } = useSidebar();
  const location = useLocation();
  const { user } = useAuth();
  const semPermissaoAlguma = ehMembro(user) && (user?.permissoes || []).length === 0;
  
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
              {semPermissaoAlguma && <AvisoSemPermissao />}
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
