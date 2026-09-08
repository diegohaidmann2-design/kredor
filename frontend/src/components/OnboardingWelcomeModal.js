import React from 'react';
import { Rocket, SkipForward } from 'lucide-react';
import { motion } from 'framer-motion';

const OnboardingWelcomeModal = ({ onStartTour, onSkip, userName }) => {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden"
      >
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-8 text-white text-center">
          <Rocket className="w-16 h-16 mx-auto mb-4" />
          <h2 className="text-3xl font-bold mb-2">Bem-vindo ao Gestor Cred! 🎉</h2>
          <p className="text-blue-100">Olá, {userName}! Vamos começar sua jornada.</p>
        </div>

        <div className="p-8">
          <p className="text-gray-700 dark:text-gray-300 mb-6 text-center">
            Preparamos um tour rápido para você conhecer as principais funcionalidades.
          </p>

          <div className="flex flex-col gap-3">
            <button
              onClick={onStartTour}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
            >
              <Rocket className="w-5 h-5" />
              Iniciar Tour (2 min)
            </button>
            <button
              onClick={onSkip}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 text-gray-600 dark:text-gray-400 hover:text-gray-800 rounded-lg"
            >
              <SkipForward className="w-4 h-4" />
              Pular por enquanto
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default OnboardingWelcomeModal;
