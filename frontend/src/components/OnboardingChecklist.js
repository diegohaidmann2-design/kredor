import React from 'react';
import { CheckCircle2, Circle, Trophy, Rocket, ChevronRight, User, Users, Wallet, CreditCard, FileText, Settings } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const TASK_ICONS = {
  perfil_completo: User,
  primeiro_cliente: Users,
  primeiro_emprestimo: Wallet,
  primeiro_pagamento: CreditCard,
  primeiro_contrato: FileText,
  configuracoes: Settings,
};

const OnboardingChecklist = ({ tasks, progress, points, totalPoints, onTaskClick, onStartTour, taskDefinitions }) => {
  const navigate = useNavigate();

  // Definição padrão das tarefas (caso não venha do backend)
  const defaultTaskDefinitions = {
    perfil_completo: {
      title: "Complete seu perfil",
      description: "Adicione suas informações básicas",
      points: 10,
      action: "/perfil",
    },
    primeiro_cliente: {
      title: "Adicione seu primeiro cliente",
      description: "Cadastre um cliente para começar",
      points: 20,
      action: "/clientes",
    },
    primeiro_emprestimo: {
      title: "Crie seu primeiro empréstimo",
      description: "Configure um empréstimo para um cliente",
      points: 30,
      action: "/emprestimos",
    },
    primeiro_pagamento: {
      title: "Registre um pagamento",
      description: "Marque uma parcela como paga",
      points: 20,
      action: "/pagamentos",
    },
    primeiro_contrato: {
      title: "Gere seu primeiro contrato",
      description: "Crie um contrato PDF para um empréstimo",
      points: 10,
      action: "/contratos",
    },
    configuracoes: {
      title: "Configure suas preferências",
      description: "Ajuste as configurações do sistema",
      points: 10,
      action: "/perfil",
    }
  };

  // Usar taskDefinitions do backend se disponível, senão usar default
  const finalTaskDefinitions = taskDefinitions || defaultTaskDefinitions;

  const completedCount = Object.values(tasks).filter(t => t).length;
  const totalTasks = Object.keys(tasks).length;

  const handleNavigate = (action) => {
    navigate(action);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900 rounded-xl p-6 shadow-lg border border-blue-200 dark:border-gray-700"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Rocket className="w-5 h-5 text-yellow-500" />
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">
              Primeiros Passos
            </h3>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Complete as tarefas abaixo para dominar o Kredor
          </p>
        </div>
        
        {progress === 100 && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="flex items-center gap-2 bg-green-100 dark:bg-green-900/30 px-3 py-1.5 rounded-full"
          >
            <Trophy className="w-4 h-4 text-green-600 dark:text-green-400" />
            <span className="text-xs font-bold text-green-700 dark:text-green-300">
              Completo!
            </span>
          </motion.div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Progresso: {completedCount}/{totalTasks} tarefas
          </span>
          <span className="text-sm font-bold text-blue-600 dark:text-blue-400">
            {points}/{totalPoints} pontos
          </span>
        </div>
        <div className="relative w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full"
          />
          {progress === 100 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 1, 0] }}
              transition={{ repeat: Infinity, duration: 2 }}
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
              style={{ transform: 'translateX(-100%)' }}
            />
          )}
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-center">
          {progress}% concluído
        </p>
      </div>

      {/* Tasks List */}
      <div className="space-y-3 mb-4">
        {Object.entries(tasks).map(([key, completed]) => {
          const task = finalTaskDefinitions[key];
          if (!task) return null;

          return (
            <motion.button
              key={key}
              onClick={() => !completed && handleNavigate(task.action)}
              className={`w-full flex items-center gap-3 p-3 rounded-lg border-2 transition-all ${
                completed
                  ? 'bg-green-50 dark:bg-green-900/20 border-green-300 dark:border-green-700'
                  : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-md'
              }`}
              whileHover={!completed ? { scale: 1.02 } : {}}
              whileTap={!completed ? { scale: 0.98 } : {}}
            >
              {/* Icon */}
              <div className="flex-shrink-0">
                {completed ? (
                  <CheckCircle2 className="w-6 h-6 text-green-600 dark:text-green-400" />
                ) : (
                  <Circle className="w-6 h-6 text-gray-400 dark:text-gray-600" />
                )}
              </div>

              {/* Ícone da tarefa */}
              {(() => {
                const TaskIcon = TASK_ICONS[key];
                return TaskIcon ? (
                  <span className="flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-md bg-muted text-muted-foreground">
                    <TaskIcon className="w-5 h-5" strokeWidth={1.5} />
                  </span>
                ) : null;
              })()}

              {/* Content */}
              <div className="flex-1 text-left">
                <h4 className={`text-sm font-semibold ${
                  completed 
                    ? 'text-green-700 dark:text-green-300 line-through' 
                    : 'text-gray-900 dark:text-white'
                }`}>
                  {task.title}
                </h4>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {task.description}
                </p>
              </div>

              {/* Points */}
              <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-bold ${
                completed
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                  : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
              }`}>
                +{task.points}
              </div>

              {/* Arrow */}
              {!completed && (
                <ChevronRight className="w-4 h-4 text-gray-400" />
              )}
            </motion.button>
          );
        })}
      </div>

      {/* Tour Button */}
      {progress < 100 && (
        <button
          onClick={onStartTour}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
        >
          <Rocket className="w-4 h-4" />
          Fazer Tour Guiado
        </button>
      )}

      {/* Completion Message */}
      {progress === 100 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-gradient-to-r from-green-100 to-emerald-100 dark:from-green-900/30 dark:to-emerald-900/30 p-4 rounded-lg text-center"
        >
          <Trophy className="w-12 h-12 text-yellow-500 mx-auto mb-2" />
          <h4 className="text-lg font-bold text-green-800 dark:text-green-200 mb-1">
            Parabéns!
          </h4>
          <p className="text-sm text-green-700 dark:text-green-300">
            Você completou o onboarding e desbloqueou todas as funcionalidades!
          </p>
        </motion.div>
      )}
    </motion.div>
  );
};

export default OnboardingChecklist;
