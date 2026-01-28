import React from 'react';

/**
 * Badge de Score com classificação colorida
 */
const ScoreBadge = ({ score, classificacao, size = 'md', showLabel = true }) => {
  // Configurações de cores por classificação
  const getClassificacaoConfig = (classe) => {
    const configs = {
      'A': {
        color: 'emerald',
        bg: 'bg-emerald-500/20',
        text: 'text-emerald-500',
        border: 'border-emerald-500/30',
        label: 'Excelente',
        icon: '🟢'
      },
      'B': {
        color: 'blue',
        bg: 'bg-blue-500/20',
        text: 'text-blue-500',
        border: 'border-blue-500/30',
        label: 'Bom',
        icon: '🔵'
      },
      'C': {
        color: 'yellow',
        bg: 'bg-yellow-500/20',
        text: 'text-yellow-500',
        border: 'border-yellow-500/30',
        label: 'Regular',
        icon: '🟡'
      },
      'D': {
        color: 'orange',
        bg: 'bg-orange-500/20',
        text: 'text-orange-500',
        border: 'border-orange-500/30',
        label: 'Risco',
        icon: '🟠'
      },
      'E': {
        color: 'red',
        bg: 'bg-red-500/20',
        text: 'text-red-500',
        border: 'border-red-500/30',
        label: 'Alto Risco',
        icon: '🔴'
      }
    };
    
    return configs[classe] || configs['C'];
  };

  const config = getClassificacaoConfig(classificacao);

  // Tamanhos
  const sizes = {
    'sm': {
      container: 'px-2 py-1',
      score: 'text-sm',
      label: 'text-xs'
    },
    'md': {
      container: 'px-3 py-1.5',
      score: 'text-base',
      label: 'text-xs'
    },
    'lg': {
      container: 'px-4 py-2',
      score: 'text-lg',
      label: 'text-sm'
    }
  };

  const sizeConfig = sizes[size] || sizes['md'];

  return (
    <div 
      className={`inline-flex items-center gap-2 ${sizeConfig.container} ${config.bg} ${config.text} border ${config.border} rounded-full font-semibold`}
      title={`Score: ${score} - Classificação: ${config.label}`}
    >
      <span className={sizeConfig.score}>{score.toFixed(1)}</span>
      {showLabel && (
        <>
          <span className="opacity-50">|</span>
          <span className={sizeConfig.label}>{config.icon} {classificacao}</span>
        </>
      )}
    </div>
  );
};

export default ScoreBadge;
