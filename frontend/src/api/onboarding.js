import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// API de Onboarding
export const onboardingAPI = {
  // Obter status do onboarding
  getStatus: () => axios.get(`${API}/api/onboarding/status`),
  
  // Obter steps do tour
  getTourSteps: () => axios.get(`${API}/api/onboarding/tour-steps`),
  
  // Iniciar onboarding
  start: () => axios.post(`${API}/api/onboarding/start`),
  
  // Atualizar step do tour
  updateTourStep: (step) => axios.post(`${API}/api/onboarding/tour/update-step`, { step }),
  
  // Finalizar tour
  finishTour: () => axios.post(`${API}/api/onboarding/tour/finish`),
  
  // Atualizar tarefa
  updateTask: (taskKey, completed) => axios.post(`${API}/api/onboarding/task/update`, {
    task_key: taskKey,
    completed
  }),
  
  // Pular onboarding
  skip: () => axios.post(`${API}/api/onboarding/skip`, { skip: true }),
  
  // Resetar onboarding (dev/test)
  reset: () => axios.post(`${API}/api/onboarding/reset`)
};

export default {
  onboardingAPI
};
