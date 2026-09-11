import React from 'react';
import { motion } from 'framer-motion';
import logomark from '../assets/logomark.png';

const Loading = ({ message = 'Carregando...', fullScreen = true }) => {
  return (
    // Tela cheia presa à viewport: no celular a página pode estar rolada ao navegar e o 100vh do
    // min-h-screen inclui a barra do navegador — nos dois casos o logo aparecia fora do centro.
    <div className={`${fullScreen ? 'fixed inset-0 z-50' : 'min-h-[400px]'} bg-background flex items-center justify-center p-4`}>
      <div className="text-center space-y-6">
        {/* Logo Kredor animado: a caixa tem o tamanho do logo, para os círculos pulsarem em volta dele */}
        <motion.div
          className="relative mx-auto w-20 h-20"
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          {/* Círculos pulsantes de fundo */}
          <motion.div
            className="absolute -inset-2 rounded-2xl bg-primary/20"
            animate={{
              scale: [1, 1.3, 1],
              opacity: [0.5, 0, 0.5],
              rotate: [0, 5, 0],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
          <motion.div
            className="absolute -inset-2 rounded-2xl bg-primary/30"
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.7, 0, 0.7],
              rotate: [0, -5, 0],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 0.3,
            }}
          />
          
          {/* Logomark Kredor */}
          <motion.img
            src={logomark}
            alt="Kredor"
            className="relative block w-20 h-20 object-contain drop-shadow-[0_8px_24px_rgba(16,185,129,0.35)]"
            animate={{
              rotate: [0, 3, -3, 0],
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        </motion.div>

        {/* Nome do sistema */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-1"
        >
          <h2 className="text-xl font-display font-bold text-foreground">
            <span className="text-primary">Kredor</span>
          </h2>
        </motion.div>

        {/* Spinner de pontos */}
        <div className="flex items-center justify-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 rounded-full bg-primary"
              animate={{
                y: [0, -8, 0],
                opacity: [0.5, 1, 0.5],
                scale: [1, 1.2, 1],
              }}
              transition={{
                duration: 0.8,
                repeat: Infinity,
                ease: "easeInOut",
                delay: i * 0.15,
              }}
            />
          ))}
        </div>

        {/* Mensagem */}
        <motion.p
          className="text-muted-foreground font-medium text-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          {message}
        </motion.p>
      </div>
    </div>
  );
};

// Mini spinner para botões e componentes pequenos
export const MiniSpinner = ({ className = '' }) => (
  <motion.div
    className={`w-5 h-5 border-2 border-current border-t-transparent rounded-full ${className}`}
    animate={{ rotate: 360 }}
    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
  />
);

// Spinner de overlay para carregamentos parciais
export const OverlaySpinner = ({ message = 'Processando...' }) => (
  <motion.div
    className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50 rounded-xl"
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
  >
    <div className="text-center space-y-4">
      {/* Mini logomark Kredor animado */}
      <motion.img
        src={logomark}
        alt="Kredor"
        className="w-12 h-12 object-contain mx-auto drop-shadow-[0_6px_16px_rgba(16,185,129,0.3)]"
        animate={{ rotate: [0, 5, -5, 0] }}
        transition={{ duration: 2, repeat: Infinity }}
      />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  </motion.div>
);

// Spinner inline com a marca Kredor
export const InlineSpinner = ({ size = 'md' }) => {
  const sizes = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-10 h-10',
  };

  return (
    <motion.img
      src={logomark}
      alt="Kredor"
      className={`${sizes[size]} object-contain`}
      animate={{
        rotate: [0, 360],
        scale: [1, 1.1, 1],
      }}
      transition={{
        rotate: { duration: 3, repeat: Infinity, ease: "linear" },
        scale: { duration: 1, repeat: Infinity, ease: "easeInOut" },
      }}
    />
  );
};

export default Loading;
