// Helpers de periodicidade (mensal, semanal, quinzenal, diario)
// Centraliza rótulos e nomes de campo para exibição consistente em toda a UI.

export const PERIODICIDADE_INFO = {
  mensal: { taxaField: 'taxa_juros_mensal', prazoField: 'prazo_meses', unidade: 'mês', plural: 'meses', curto: 'mês', adv: 'mensalmente' },
  semanal: { taxaField: 'taxa_juros_semanal', prazoField: 'prazo_semanas', unidade: 'semana', plural: 'semanas', curto: 'sem', adv: 'semanalmente' },
  quinzenal: { taxaField: 'taxa_juros_quinzenal', prazoField: 'prazo_quinzenas', unidade: 'quinzena', plural: 'quinzenas', curto: 'quinz', adv: 'quinzenalmente' },
  diario: { taxaField: 'taxa_juros_diaria', prazoField: 'prazo_dias', unidade: 'dia', plural: 'dias', curto: 'dia', adv: 'diariamente' },
};

export const infoPeriodicidade = (p) => PERIODICIDADE_INFO[p] || PERIODICIDADE_INFO.mensal;

// Taxa efetiva de um empréstimo conforme a periodicidade
export const taxaDoEmprestimo = (emp) => {
  if (!emp) return null;
  const info = infoPeriodicidade(emp.periodicidade);
  return emp[info.taxaField] ?? emp.taxa_juros_mensal ?? null;
};

// Prazo efetivo de um empréstimo conforme a periodicidade
export const prazoDoEmprestimo = (emp) => {
  if (!emp) return null;
  const info = infoPeriodicidade(emp.periodicidade);
  return emp[info.prazoField] ?? emp.prazo_meses ?? null;
};
