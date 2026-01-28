import React, { useState, useEffect } from 'react';
import { X, ChevronLeft, ChevronRight, SkipForward } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const OnboardingTour = ({ steps, currentStep, onNext, onPrev, onSkip, onFinish }) => {
  const [activeStep, setActiveStep] = useState(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  useEffect(() => {
    if (currentStep >= 0 && currentStep < steps.length) {
      const step = steps[currentStep];
      setActiveStep(step);
      
      // Encontrar elemento alvo e posicionar tooltip
      const targetElement = document.querySelector(step.target);
      if (targetElement) {
        const rect = targetElement.getBoundingClientRect();
        
        // Adicionar highlight no elemento
        targetElement.classList.add('onboarding-highlight');
        
        // Calcular posição do tooltip baseado no placement
        let top, left;
        switch (step.placement) {
          case 'right':
            top = rect.top + rect.height / 2 - 100;
            left = rect.right + 20;
            break;
          case 'left':
            top = rect.top + rect.height / 2 - 100;
            left = rect.left - 320;
            break;
          case 'bottom':
            top = rect.bottom + 20;
            left = rect.left + rect.width / 2 - 150;
            break;
          case 'top':
            top = rect.top - 220;
            left = rect.left + rect.width / 2 - 150;
            break;
          default:
            top = rect.top;
            left = rect.right + 20;
        }
        
        setPosition({ top, left });
        
        // Scroll suave para o elemento
        targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
    
    // Cleanup: remover highlights de steps anteriores
    return () => {
      document.querySelectorAll('.onboarding-highlight').forEach(el => {
        el.classList.remove('onboarding-highlight');
      });
    };
  }, [currentStep, steps]);

  if (!activeStep) return null;

  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;

  return (
    <>
      {/* Overlay escuro */}
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 z-[9998]"
          style={{ pointerEvents: 'none' }}
        />
      </AnimatePresence>

      {/* Tooltip do tour */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="fixed z-[9999] bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6 w-80"
        style={{
          top: `${position.top}px`,
          left: `${position.left}px`,
        }}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">
              {activeStep.title}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Passo {currentStep + 1} de {steps.length}
            </p>
          </div>
          <button
            onClick={onSkip}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-6">
          {activeStep.content}
        </p>

        {/* Progress bar */}
        <div className="mb-4">
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
            <div
              className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between gap-2">
          <button
            onClick={onPrev}
            disabled={isFirstStep}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
            Anterior
          </button>

          <button
            onClick={onSkip}
            className="flex items-center gap-2 px-3 py-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 transition-colors"
          >
            <SkipForward className="w-4 h-4" />
            Pular tour
          </button>

          {isLastStep ? (
            <button
              onClick={onFinish}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
            >
              Finalizar
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={onNext}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              Próximo
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </motion.div>

      {/* CSS para highlight */}
      <style>{`
        .onboarding-highlight {
          position: relative;
          z-index: 9999 !important;
          box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.5), 0 0 0 9999px rgba(0, 0, 0, 0.5) !important;
          border-radius: 8px;
          animation: pulse-highlight 2s infinite;
        }
        
        @keyframes pulse-highlight {
          0%, 100% {
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.5), 0 0 0 9999px rgba(0, 0, 0, 0.5);
          }
          50% {
            box-shadow: 0 0 0 8px rgba(59, 130, 246, 0.3), 0 0 0 9999px rgba(0, 0, 0, 0.5);
          }
        }
      `}</style>
    </>
  );
};

export default OnboardingTour;
