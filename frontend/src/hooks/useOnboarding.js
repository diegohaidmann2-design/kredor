import { useState, useEffect } from 'react';
import { onboardingAPI } from '../api/onboarding';

export const useOnboarding = () => {
  const [onboarding, setOnboarding] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showWelcome, setShowWelcome] = useState(false);
  const [showTour, setShowTour] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [tourSteps, setTourSteps] = useState([]);

  // Carregar status do onboarding
  const loadStatus = async () => {
    try {
      setLoading(true);
      const response = await onboardingAPI.getStatus();
      const data = response.data.onboarding;
      setOnboarding(data);

      // Verificar se deve mostrar o modal de boas-vindas
      if (!data.started_at && !data.completed) {
        setShowWelcome(true);
      }

      setLoading(false);
    } catch (error) {
      console.error('Erro ao carregar onboarding:', error);
      setLoading(false);
    }
  };

  // Carregar steps do tour
  const loadTourSteps = async () => {
    try {
      const response = await onboardingAPI.getTourSteps();
      setTourSteps(response.data.steps);
    } catch (error) {
      console.error('Erro ao carregar tour steps:', error);
    }
  };

  useEffect(() => {
    loadStatus();
    loadTourSteps();
  }, []);

  // Iniciar tour
  const startTour = async () => {
    try {
      await onboardingAPI.start();
      setShowWelcome(false);
      setShowTour(true);
      setCurrentStep(0);
    } catch (error) {
      console.error('Erro ao iniciar tour:', error);
    }
  };

  // Próximo step
  const nextStep = async () => {
    const newStep = currentStep + 1;
    if (newStep < tourSteps.length) {
      setCurrentStep(newStep);
      await onboardingAPI.updateTourStep(newStep);
    } else {
      await finishTour();
    }
  };

  // Step anterior
  const prevStep = () => {
    if (currentStep > 0) {
      const newStep = currentStep - 1;
      setCurrentStep(newStep);
      onboardingAPI.updateTourStep(newStep);
    }
  };

  // Finalizar tour
  const finishTour = async () => {
    try {
      await onboardingAPI.finishTour();
      setShowTour(false);
      await loadStatus();
    } catch (error) {
      console.error('Erro ao finalizar tour:', error);
    }
  };

  // Pular onboarding
  const skipOnboarding = async () => {
    try {
      await onboardingAPI.skip();
      setShowWelcome(false);
      setShowTour(false);
      await loadStatus();
    } catch (error) {
      console.error('Erro ao pular onboarding:', error);
    }
  };

  // Atualizar tarefa
  const updateTask = async (taskKey, completed) => {
    try {
      await onboardingAPI.updateTask(taskKey, completed);
      await loadStatus();
    } catch (error) {
      console.error('Erro ao atualizar tarefa:', error);
    }
  };

  // Resetar (dev only)
  const resetOnboarding = async () => {
    try {
      await onboardingAPI.reset();
      await loadStatus();
      setShowWelcome(true);
    } catch (error) {
      console.error('Erro ao resetar onboarding:', error);
    }
  };

  return {
    onboarding,
    loading,
    showWelcome,
    showTour,
    currentStep,
    tourSteps,
    startTour,
    nextStep,
    prevStep,
    finishTour,
    skipOnboarding,
    updateTask,
    resetOnboarding,
    refreshStatus: loadStatus
  };
};
