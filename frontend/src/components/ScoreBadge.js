import React from 'react';

/**
 * Badge de Score neo-brutalista: canto reto suave, ring interno, ponto colorido.
 */
const ScoreBadge = ({ score, classificacao, size = 'md', showLabel = true }) => {
  const getClassificacaoConfig = (classe) => {
    const configs = {
      'A': { dot: 'bg-emerald-500', ring: 'bg-emerald-500/10 text-emerald-500 ring-emerald-500/20', label: 'Excelente' },
      'B': { dot: 'bg-blue-500', ring: 'bg-blue-500/10 text-blue-500 ring-blue-500/20', label: 'Bom' },
      'C': { dot: 'bg-amber-500', ring: 'bg-amber-500/10 text-amber-500 ring-amber-500/20', label: 'Regular' },
      'D': { dot: 'bg-orange-500', ring: 'bg-orange-500/10 text-orange-500 ring-orange-500/20', label: 'Risco' },
      'E': { dot: 'bg-rose-500', ring: 'bg-rose-500/10 text-rose-500 ring-rose-500/20', label: 'Alto Risco' },
    };
    return configs[classe] || configs['C'];
  };

  const config = getClassificacaoConfig(classificacao);

  const sizes = {
    'sm': { container: 'px-2 py-1', score: 'text-sm', label: 'text-xs' },
    'md': { container: 'px-3 py-1.5', score: 'text-base', label: 'text-xs' },
    'lg': { container: 'px-4 py-2', score: 'text-lg', label: 'text-sm' },
  };
  const sizeConfig = sizes[size] || sizes['md'];

  return (
    <div
      className={`inline-flex items-center gap-2 ${sizeConfig.container} ${config.ring} ring-1 ring-inset rounded-md font-semibold`}
      title={`Score: ${score} - Classificação: ${config.label}`}
    >
      <span className={`font-mono ${sizeConfig.score}`}>{score.toFixed(1)}</span>
      {showLabel && (
        <>
          <span className="opacity-40">|</span>
          <span className={`inline-flex items-center gap-1.5 uppercase tracking-wider ${sizeConfig.label}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
            {classificacao}
          </span>
        </>
      )}
    </div>
  );
};

export default ScoreBadge;
