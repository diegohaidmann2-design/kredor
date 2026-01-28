import React, { createContext, useContext, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Info, 
  X,
  Sparkles
} from 'lucide-react';

// Contexto do Modal
const ModalContext = createContext(null);

// Hook para usar o modal
export const useModal = () => {
  const context = useContext(ModalContext);
  if (!context) {
    throw new Error('useModal deve ser usado dentro de ModalProvider');
  }
  return context;
};

// Tipos de modal
const MODAL_TYPES = {
  success: {
    icon: CheckCircle,
    color: 'emerald',
    bgGradient: 'from-emerald-500/20 to-green-500/20',
    borderColor: 'border-emerald-500/50',
    iconBg: 'bg-emerald-500/20',
    iconColor: 'text-emerald-400',
    buttonBg: 'bg-emerald-500 hover:bg-emerald-600',
  },
  error: {
    icon: XCircle,
    color: 'red',
    bgGradient: 'from-red-500/20 to-rose-500/20',
    borderColor: 'border-red-500/50',
    iconBg: 'bg-red-500/20',
    iconColor: 'text-red-400',
    buttonBg: 'bg-red-500 hover:bg-red-600',
  },
  warning: {
    icon: AlertTriangle,
    color: 'amber',
    bgGradient: 'from-amber-500/20 to-yellow-500/20',
    borderColor: 'border-amber-500/50',
    iconBg: 'bg-amber-500/20',
    iconColor: 'text-amber-400',
    buttonBg: 'bg-amber-500 hover:bg-amber-600',
  },
  info: {
    icon: Info,
    color: 'blue',
    bgGradient: 'from-blue-500/20 to-cyan-500/20',
    borderColor: 'border-blue-500/50',
    iconBg: 'bg-blue-500/20',
    iconColor: 'text-blue-400',
    buttonBg: 'bg-blue-500 hover:bg-blue-600',
  },
};

// Componente do Modal
const Modal = ({ isOpen, onClose, type = 'info', title, message, confirmText = 'OK', onConfirm, cancelText, onCancel, children }) => {
  const config = MODAL_TYPES[type] || MODAL_TYPES.info;
  const IconComponent = config.icon;

  const handleConfirm = () => {
    if (onConfirm) onConfirm();
    onClose();
  };

  const handleCancel = () => {
    if (onCancel) onCancel();
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ 
              type: "spring", 
              damping: 25, 
              stiffness: 300,
              duration: 0.3 
            }}
            className="fixed inset-0 flex items-center justify-center z-[101] p-4"
          >
            <div className={`
              relative w-full max-w-md
              bg-gradient-to-br ${config.bgGradient}
              bg-slate-900/95 backdrop-blur-xl
              border ${config.borderColor}
              rounded-2xl shadow-2xl
              overflow-hidden
            `}>
              {/* Efeito de brilho */}
              <div className="absolute inset-0 overflow-hidden">
                <motion.div
                  animate={{
                    rotate: [0, 360],
                  }}
                  transition={{
                    duration: 8,
                    repeat: Infinity,
                    ease: "linear"
                  }}
                  className={`absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-conic from-${config.color}-500/20 via-transparent to-transparent`}
                />
              </div>

              {/* Botão fechar */}
              <button
                onClick={onClose}
                className="absolute top-4 right-4 p-1 text-slate-400 hover:text-white transition-colors z-10"
              >
                <X className="w-5 h-5" />
              </button>

              {/* Conteúdo */}
              <div className="relative p-6 pt-8">
                {/* Ícone */}
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ 
                    type: "spring", 
                    delay: 0.1,
                    damping: 15,
                    stiffness: 200
                  }}
                  className="flex justify-center mb-4"
                >
                  <div className={`p-4 rounded-full ${config.iconBg}`}>
                    <IconComponent className={`w-12 h-12 ${config.iconColor}`} />
                  </div>
                </motion.div>

                {/* Título */}
                <motion.h3
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15 }}
                  className="text-xl font-bold text-white text-center mb-2"
                >
                  {title}
                </motion.h3>

                {/* Mensagem */}
                <motion.p
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="text-slate-300 text-center mb-6"
                >
                  {message}
                </motion.p>

                {/* Conteúdo customizado */}
                {children && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.25 }}
                    className="mb-6"
                  >
                    {children}
                  </motion.div>
                )}

                {/* Botões */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25 }}
                  className={`flex gap-3 ${cancelText ? 'justify-between' : 'justify-center'}`}
                >
                  {cancelText && (
                    <button
                      onClick={handleCancel}
                      className="flex-1 px-6 py-3 bg-slate-700/50 hover:bg-slate-700 text-white font-medium rounded-xl transition-all duration-200"
                    >
                      {cancelText}
                    </button>
                  )}
                  <button
                    onClick={handleConfirm}
                    className={`flex-1 px-6 py-3 ${config.buttonBg} text-white font-medium rounded-xl transition-all duration-200 shadow-lg`}
                  >
                    {confirmText}
                  </button>
                </motion.div>
              </div>

              {/* Partículas decorativas */}
              <Sparkles className={`absolute top-4 left-4 w-4 h-4 ${config.iconColor} opacity-50`} />
              <Sparkles className={`absolute bottom-4 right-12 w-3 h-3 ${config.iconColor} opacity-30`} />
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

// Provider do Modal
export const ModalProvider = ({ children }) => {
  const [modalState, setModalState] = useState({
    isOpen: false,
    type: 'info',
    title: '',
    message: '',
    confirmText: 'OK',
    cancelText: null,
    onConfirm: null,
    onCancel: null,
    customContent: null,
  });

  const showModal = useCallback(({
    type = 'info',
    title,
    message,
    confirmText = 'OK',
    cancelText = null,
    onConfirm = null,
    onCancel = null,
    customContent = null,
  }) => {
    setModalState({
      isOpen: true,
      type,
      title,
      message,
      confirmText,
      cancelText,
      onConfirm,
      onCancel,
      customContent,
    });
  }, []);

  const closeModal = useCallback(() => {
    setModalState(prev => ({ ...prev, isOpen: false }));
  }, []);

  // Métodos de conveniência
  const success = useCallback((title, message, options = {}) => {
    showModal({ type: 'success', title, message, ...options });
  }, [showModal]);

  const error = useCallback((title, message, options = {}) => {
    showModal({ type: 'error', title, message, ...options });
  }, [showModal]);

  const warning = useCallback((title, message, options = {}) => {
    showModal({ type: 'warning', title, message, ...options });
  }, [showModal]);

  const info = useCallback((title, message, options = {}) => {
    showModal({ type: 'info', title, message, ...options });
  }, [showModal]);

  const confirm = useCallback((title, message, onConfirm, onCancel = null) => {
    showModal({
      type: 'warning',
      title,
      message,
      confirmText: 'Confirmar',
      cancelText: 'Cancelar',
      onConfirm,
      onCancel,
    });
  }, [showModal]);

  return (
    <ModalContext.Provider value={{ showModal, closeModal, success, error, warning, info, confirm }}>
      {children}
      <Modal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        type={modalState.type}
        title={modalState.title}
        message={modalState.message}
        confirmText={modalState.confirmText}
        cancelText={modalState.cancelText}
        onConfirm={modalState.onConfirm}
        onCancel={modalState.onCancel}
      >
        {modalState.customContent}
      </Modal>
    </ModalContext.Provider>
  );
};

export default Modal;
