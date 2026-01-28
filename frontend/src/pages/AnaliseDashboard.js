import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import { analiseAPI } from '../api/api';
import { TrendingUp, TrendingDown, Users, CheckCircle, AlertCircle, XCircle, BarChart3, Target } from 'lucide-react';

const AnaliseDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [dados, setDados] = useState(null);
  const [periodo, setPeriodo] = useState('30d');

  useEffect(() => {
    carregarDados();
  }, [periodo]);

  const carregarDados = async () => {
    try {
      setLoading(true);
      const response = await analiseAPI.obterDashboard({ periodo });
      setDados(response.data);
    } catch (error) {
      console.error('Erro ao carregar dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading message="Carregando análise..." />;
  if (!dados) return <div className="p-8 text-center text-muted-foreground">Erro ao carregar dados</div>;

  const { resumo, distribuicao_classificacao, score_medio, tendencias, evolucao_mensal } = dados;

  // Dados para gráfico de pizza - filtrar valores zero
  const dadosPizzaCompleto = [
    { name: 'Excelente', letra: 'A', value: distribuicao_classificacao.A, color: '#10b981' },
    { name: 'Bom', letra: 'B', value: distribuicao_classificacao.B, color: '#3b82f6' },
    { name: 'Regular', letra: 'C', value: distribuicao_classificacao.C, color: '#eab308' },
    { name: 'Risco', letra: 'D', value: distribuicao_classificacao.D, color: '#f97316' },
    { name: 'Alto Risco', letra: 'E', value: distribuicao_classificacao.E, color: '#ef4444' },
  ];
  
  // Filtrar apenas valores > 0 para o gráfico
  const dadosPizza = dadosPizzaCompleto.filter(item => item.value > 0);

  // Dados para gráfico de linha (evolução)
  const dadosEvolucao = evolucao_mensal.length > 0 
    ? evolucao_mensal.map(item => ({
        mes: new Date(item.mes).toLocaleDateString('pt-BR', { month: 'short' }),
        score: item.score_medio
      }))
    : [{ mes: 'Atual', score: score_medio }];

  const variacao = tendencias.variacao;
  const variacaoPositiva = variacao >= 0;

  // Calcular porcentagem segura
  const calcularPorcentagem = (valor) => {
    if (!resumo.total_clientes || resumo.total_clientes === 0) return '0.0';
    return ((valor / resumo.total_clientes) * 100).toFixed(1);
  };

  // Obter classificação do score médio
  const getScoreClassificacao = (score) => {
    if (score >= 85) return { label: 'Excelente', color: 'text-emerald-500', bg: 'bg-emerald-500/20' };
    if (score >= 70) return { label: 'Bom', color: 'text-blue-500', bg: 'bg-blue-500/20' };
    if (score >= 50) return { label: 'Regular', color: 'text-yellow-500', bg: 'bg-yellow-500/20' };
    if (score >= 30) return { label: 'Risco', color: 'text-orange-500', bg: 'bg-orange-500/20' };
    return { label: 'Alto Risco', color: 'text-red-500', bg: 'bg-red-500/20' };
  };

  const scoreClass = getScoreClassificacao(score_medio);

  // Custom label para o gráfico de pizza (fora do gráfico)
  const renderCustomLabel = ({ cx, cy, midAngle, outerRadius, letra, percent }) => {
    const RADIAN = Math.PI / 180;
    const radius = outerRadius + 25;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    
    return (
      <text 
        x={x} 
        y={y} 
        fill="#9ca3af" 
        textAnchor={x > cx ? 'start' : 'end'} 
        dominantBaseline="central"
        className="text-sm font-medium"
      >
        {`${letra}: ${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-8">
        {/* Header com melhor espaçamento */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-display font-bold text-foreground">
              Análise de Clientes
            </h1>
            <p className="text-muted-foreground mt-2 text-base">
              Score de crédito e classificação de risco
            </p>
          </div>
          
          {/* Seletor de Período */}
          <select
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            className="px-4 py-2.5 bg-card border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary min-w-[180px]"
            data-testid="periodo-select"
          >
            <option value="30d">Últimos 30 dias</option>
            <option value="90d">Últimos 90 dias</option>
            <option value="1y">Último ano</option>
            <option value="all">Todo período</option>
          </select>
        </div>

        {/* Cards de Indicadores com padding melhorado */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
          {/* Total de Clientes */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-card rounded-xl border border-border p-6 hover:border-primary/30 transition-colors"
            data-testid="card-total-clientes"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-muted-foreground">Total de Clientes</p>
                <p className="text-4xl font-bold text-foreground mt-3">{resumo.total_clientes}</p>
                <p className="text-sm text-muted-foreground mt-2">cadastrados no sistema</p>
              </div>
              <div className="w-14 h-14 bg-primary/20 rounded-xl flex items-center justify-center flex-shrink-0">
                <Users className="w-7 h-7 text-primary" />
              </div>
            </div>
          </motion.div>

          {/* Bons Pagadores */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-card rounded-xl border border-border p-6 hover:border-emerald-500/30 transition-colors"
            data-testid="card-bons-pagadores"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-muted-foreground">Bons Pagadores</p>
                <p className="text-4xl font-bold text-emerald-500 mt-3">{resumo.bons_pagadores}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-sm text-muted-foreground">{calcularPorcentagem(resumo.bons_pagadores)}%</span>
                  <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-500 rounded text-xs font-medium">A/B</span>
                </div>
              </div>
              <div className="w-14 h-14 bg-emerald-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
                <CheckCircle className="w-7 h-7 text-emerald-500" />
              </div>
            </div>
          </motion.div>

          {/* Pagadores Regulares (Classe C) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-card rounded-xl border border-border p-6 hover:border-yellow-500/30 transition-colors"
            data-testid="card-irregulares"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-muted-foreground">Regulares</p>
                <p className="text-4xl font-bold text-yellow-500 mt-3">{resumo.pagadores_irregulares}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-sm text-muted-foreground">{calcularPorcentagem(resumo.pagadores_irregulares)}%</span>
                  <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-500 rounded text-xs font-medium">C</span>
                </div>
              </div>
              <div className="w-14 h-14 bg-yellow-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
                <AlertCircle className="w-7 h-7 text-yellow-500" />
              </div>
            </div>
          </motion.div>

          {/* Inadimplentes */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-card rounded-xl border border-border p-6 hover:border-red-500/30 transition-colors"
            data-testid="card-inadimplentes"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-muted-foreground">Inadimplentes</p>
                <p className="text-4xl font-bold text-red-500 mt-3">{resumo.inadimplentes}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-sm text-muted-foreground">{calcularPorcentagem(resumo.inadimplentes)}%</span>
                  <span className="px-2 py-0.5 bg-red-500/20 text-red-500 rounded text-xs font-medium">D/E</span>
                </div>
              </div>
              <div className="w-14 h-14 bg-red-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
                <XCircle className="w-7 h-7 text-red-500" />
              </div>
            </div>
          </motion.div>
        </div>

        {/* Score Médio - Card destacado */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-gradient-to-r from-card to-card/80 rounded-xl border border-border p-8"
          data-testid="card-score-medio"
        >
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className={`w-16 h-16 ${scoreClass.bg} rounded-xl flex items-center justify-center`}>
                <Target className={`w-8 h-8 ${scoreClass.color}`} />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-foreground">Score Médio da Carteira</h3>
                <p className="text-sm text-muted-foreground mt-1">Baseado em todos os clientes ativos</p>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-center sm:text-right">
                <div className={`text-5xl font-bold ${scoreClass.color}`}>{score_medio.toFixed(1)}</div>
                <div className={`inline-flex items-center gap-1.5 mt-2 px-3 py-1 ${scoreClass.bg} rounded-full`}>
                  <span className={`text-sm font-semibold ${scoreClass.color}`}>{scoreClass.label}</span>
                </div>
              </div>
              <div className={`flex flex-col items-center gap-1 px-4 py-2 rounded-lg ${variacaoPositiva ? 'bg-emerald-500/10' : 'bg-red-500/10'}`}>
                {variacaoPositiva ? (
                  <TrendingUp className="w-6 h-6 text-emerald-500" />
                ) : (
                  <TrendingDown className="w-6 h-6 text-red-500" />
                )}
                <span className={`text-sm font-bold ${variacaoPositiva ? 'text-emerald-500' : 'text-red-500'}`}>
                  {variacaoPositiva ? '+' : ''}{variacao.toFixed(1)}
                </span>
                <span className="text-xs text-muted-foreground">pts</span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Gráficos lado a lado */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Gráfico de Pizza - Distribuição */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-card rounded-xl border border-border p-6"
            data-testid="chart-distribuicao"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-primary/20 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-primary" />
              </div>
              <h3 className="text-lg font-semibold text-foreground">
                Distribuição por Classificação
              </h3>
            </div>
            
            {dadosPizza.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={dadosPizza}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={renderCustomLabel}
                      outerRadius={90}
                      innerRadius={45}
                      fill="#8884d8"
                      dataKey="value"
                      paddingAngle={2}
                    >
                      {dadosPizza.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} strokeWidth={0} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--popover))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                        color: 'hsl(var(--popover-foreground))'
                      }}
                      itemStyle={{
                        color: 'hsl(var(--popover-foreground))'
                      }}
                      labelStyle={{
                        color: 'hsl(var(--popover-foreground))',
                        fontWeight: 600
                      }}
                      formatter={(value, name, props) => [
                        `${value} cliente(s)`,
                        props.payload.name
                      ]}
                    />
                  </PieChart>
                </ResponsiveContainer>
                
                {/* Legenda melhorada */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-6 pt-4 border-t border-border">
                  {dadosPizzaCompleto.map((item, index) => (
                    <div key={index} className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-muted/50 transition-colors">
                      <div 
                        className="w-3.5 h-3.5 rounded-full flex-shrink-0" 
                        style={{ backgroundColor: item.color }}
                      />
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="text-sm font-medium text-foreground">{item.letra}</span>
                        <span className="text-sm text-muted-foreground truncate">{item.name}</span>
                        <span className="text-sm font-semibold text-foreground ml-auto">{item.value}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-muted-foreground">
                Nenhum dado disponível
              </div>
            )}
          </motion.div>

          {/* Gráfico de Linha - Evolução */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="bg-card rounded-xl border border-border p-6"
            data-testid="chart-evolucao"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-blue-500" />
              </div>
              <h3 className="text-lg font-semibold text-foreground">
                Evolução do Score Médio
              </h3>
            </div>
            
            {dadosEvolucao.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={dadosEvolucao} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                  <XAxis 
                    dataKey="mes" 
                    stroke="hsl(var(--muted-foreground))" 
                    tick={{ fontSize: 12 }}
                    axisLine={{ stroke: 'hsl(var(--border))' }}
                  />
                  <YAxis 
                    domain={[0, 100]} 
                    stroke="hsl(var(--muted-foreground))" 
                    tick={{ fontSize: 12 }}
                    axisLine={{ stroke: 'hsl(var(--border))' }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'hsl(var(--popover))', 
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                      color: 'hsl(var(--popover-foreground))'
                    }}
                    itemStyle={{
                      color: 'hsl(var(--popover-foreground))'
                    }}
                    labelStyle={{ 
                      color: 'hsl(var(--popover-foreground))', 
                      fontWeight: 600 
                    }}
                    formatter={(value) => [`${value.toFixed(1)} pts`, 'Score']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="score" 
                    stroke="#3b82f6" 
                    strokeWidth={3}
                    dot={{ fill: '#3b82f6', r: 5, strokeWidth: 2, stroke: 'hsl(var(--card))' }}
                    activeDot={{ r: 7, stroke: '#3b82f6', strokeWidth: 2 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[320px] flex flex-col items-center justify-center text-muted-foreground gap-2">
                <BarChart3 className="w-12 h-12 opacity-30" />
                <p>Dados insuficientes para exibir evolução</p>
                <p className="text-sm">Continue registrando pagamentos para ver o histórico</p>
              </div>
            )}
          </motion.div>
        </div>

        {/* Botão para ver lista completa */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="flex justify-center pt-4"
        >
          <a
            href="/analise/clientes"
            className="inline-flex items-center gap-3 px-8 py-4 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 transition-all font-semibold text-lg shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 hover:scale-[1.02]"
            data-testid="btn-ver-clientes"
          >
            Ver Lista Completa de Clientes
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </a>
        </motion.div>
        </div>
      </div>
    </Layout>
  );
};

export default AnaliseDashboard;
