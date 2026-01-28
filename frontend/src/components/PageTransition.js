import React from 'react';
import { motion } from 'framer-motion';

// Variantes de animação para páginas
const pageVariants = {
  initial: {
    opacity: 0,
    y: 20,
  },
  enter: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0.25, 0.46, 0.45, 0.94],
      when: "beforeChildren",
      staggerChildren: 0.1,
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

// Variantes para itens filhos (cards, sections)
const itemVariants = {
  initial: {
    opacity: 0,
    y: 20,
  },
  enter: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0.25, 0.46, 0.45, 0.94],
    },
  },
};

// Variante para fade simples
const fadeVariants = {
  initial: { opacity: 0 },
  enter: { 
    opacity: 1,
    transition: { duration: 0.3 }
  },
  exit: { 
    opacity: 0,
    transition: { duration: 0.2 }
  },
};

// Variante para slide da esquerda
const slideLeftVariants = {
  initial: { opacity: 0, x: -30 },
  enter: { 
    opacity: 1, 
    x: 0,
    transition: { duration: 0.4, ease: "easeOut" }
  },
  exit: { 
    opacity: 0, 
    x: 30,
    transition: { duration: 0.2 }
  },
};

// Variante para scale
const scaleVariants = {
  initial: { opacity: 0, scale: 0.95 },
  enter: { 
    opacity: 1, 
    scale: 1,
    transition: { duration: 0.3, ease: "easeOut" }
  },
  exit: { 
    opacity: 0, 
    scale: 0.95,
    transition: { duration: 0.2 }
  },
};

// Componente principal de transição de página
export const PageTransition = ({ children, className = '' }) => {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="enter"
      exit="exit"
      className={className}
    >
      {children}
    </motion.div>
  );
};

// Wrapper para itens animados (cards, sections)
export const AnimatedItem = ({ children, delay = 0, className = '' }) => {
  return (
    <motion.div
      variants={itemVariants}
      initial="initial"
      animate="enter"
      transition={{ delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
};

// Fade in simples
export const FadeIn = ({ children, delay = 0, className = '' }) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
};

// Slide up animado
export const SlideUp = ({ children, delay = 0, className = '' }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
};

// Container com stagger para filhos
export const StaggerContainer = ({ children, className = '', staggerDelay = 0.1 }) => {
  return (
    <motion.div
      initial="initial"
      animate="enter"
      variants={{
        initial: {},
        enter: {
          transition: {
            staggerChildren: staggerDelay,
          },
        },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
};

// Item do stagger
export const StaggerItem = ({ children, className = '' }) => {
  return (
    <motion.div
      variants={{
        initial: { opacity: 0, y: 20 },
        enter: { 
          opacity: 1, 
          y: 0,
          transition: { duration: 0.4, ease: "easeOut" }
        },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
};

// Hover scale para cards
export const HoverScale = ({ children, className = '', scale = 1.02 }) => {
  return (
    <motion.div
      whileHover={{ scale }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.2 }}
      className={className}
    >
      {children}
    </motion.div>
  );
};

export { pageVariants, itemVariants, fadeVariants, slideLeftVariants, scaleVariants };
export default PageTransition;
