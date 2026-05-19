import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import Header from '../components/Header';
import Loading from '../components/Loading';
import { useModal } from '../components/Modal';
import { useAuth } from '../context/AuthContext';
import { dashboardAPI } from '../api/api';
import { formatarMoeda, formatarData } from '../utils/formatters';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import OnboardingWelcomeModal from '../components/OnboardingWelcomeModal';
import OnboardingTour from '../components/OnboardingTour';
import OnboardingChecklist from '../components/OnboardingChecklist';
import PagamentosPendentesSection from '../components/PagamentosPendentesSection';
import { useOnboarding } from '../hooks/useOnboarding';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  Users,
  AlertTriangle,
  ArrowUpRight,
  Calendar,
  Plus,
  ChevronDown,
  Loader2,
} from 'lucide-react';

const COLORS = ['hsl(160, 84%, 39%)', 'hsl(199, 89%, 48%)', 'hsl(0, 72%, 51%)', 'hsl(215, 20%, 55%)', 'hsl(280, 65%, 60%)'];

// Animação stagger para cards
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0.25, 0.46, 0.45, 0.94],
    },
  },
};

const StatCard = ({ title, value, icon: Icon, trend, change, accent, index = 0 }) => {
  return (
    <motion.div
      variants={itemVariants}
      whileHover={{ scale: 1.02, transition: { duration: 0.2 } }}
      whileTap={{ scale: 0.98 }}
    >
      <Card className={`relative overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-primary/5 ${accent ? 'border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10' : ''
        }`}>
        <CardContent className="p-4 sm:p-6">
          <div className="flex items-start justify-between">
            <div className="space-y-1 sm:space-y-2 min-w-0 flex-1">
              <p className="text-xs sm:text-sm font-medium text-muted-foreground truncate">{title}</p>
              <motion.p
                className="text-lg sm:text-2xl font-display font-bold tracking-tight text-foreground truncate"
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 + index * 0.05, duration: 0.3 }}
              >
                {value}
              </motion.p>
              {change !== undefined && (
                <div className={`flex items-center gap-1 text-xs sm:text-sm font-medium ${trend === "up" ? "text-primary" : "text-destructive"
                  }`}>
                  {trend === "up" ? (
                    <ArrowUpRight className="w-3 h-3 sm:w-4 sm:h-4" />
                  ) : (
                    <TrendingDown className="w-3 h-3 sm:w-4 sm:h-4" />
                  )}
                  <span className="truncate">{change}% vs mês anterior</span>
                </div>
              )}
            </div>
            <motion.div
              className={`p-2 sm:p-3 rounded-xl flex-shrink-0 ${accent ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
                }`}
              whileHover={{ rotate: 5 }}
            >
              <Icon className="w-4 h-4 sm:w-5 sm:h-5" />
            </motion.div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
};

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [chartsReady, setChartsReady] = useState(false);
  const [showActionsMenu, setShowActionsMenu] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const modal = useModal();
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();

  // Hook de onboarding
  const {
    onboarding,
    loading: onboardingLoading,
    showWelcome,
    showTour,
    currentStep,
    tourSteps,
    startTour,
    nextStep,
    prevStep,
    finishTour,
    skipOnboarding,
    updateTask
  } = useOnboarding();

  useEffect(() => {
    carregarDashboard();
  }, []);

  // Polling automático após pagamento (verifica a cada 3 segundos por até 30 segundos)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const isPagamentoSucesso = urlParams.get('pagamento') === 'sucesso';

    if (isPagamentoSucesso && error && retryCount < 10) {
      const timer = setTimeout(() => {
        setRetryCount(retryCount + 1);
        carregarDashboard();
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, [error, retryCount]);

  useEffect(() => {
    // Garantir que os charts só renderizem após o DOM e dados estarem prontos
    if (stats && !loading) {
      const timer = setTimeout(() => setChartsReady(true), 300);
      return () => clearTimeout(timer);
    }
  }, [stats, loading]);

  const carregarDashboard = async () => {
    try {
      setLoading(true);
      setError('');
      // Atualizar dados do usuário também
      await refreshUser();
      const response = await dashboardAPI.obterStats();
      setStats(response.data);

      // Se chegou aqui com sucesso após pagamento, limpar query param
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('pagamento') === 'sucesso') {
        window.history.replaceState({}, '', '/dashboard');
      }
    } catch (err) {
      console.error('Erro ao carregar dashboard:', err);

      // Verificar se é erro 403 (plano inativo)
      if (err.response?.status === 403) {
        const errorMessage = err.response?.data?.detail || 'Seu plano está inativo';

        // Se tem query param de pagamento sucesso, mostrar mensagem especial
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('pagamento') === 'sucesso') {
          setError(`✅ Pagamento processado! Ativando seu plano... (Tentativa ${retryCount + 1}/10)`);
        } else {
          setError(errorMessage);
        }
      } else {
        setError('Erro ao carregar dashboard');
      }
    } finally {
      setLoading(false);
    }
  };

  const acoes = [
    { label: 'Novo Cliente', onClick: () => navigate('/clientes'), icon: Users },
    { label: 'Novo Empréstimo', onClick: () => navigate('/emprestimos'), icon: Wallet },
    { label: 'Registrar Pagamento', onClick: () => navigate('/pagamentos'), icon: TrendingUp },
    { label: 'Gerar Relatório', onClick: () => navigate('/relatorios'), icon: Calendar },
  ];

  if (loading) return <Loading message="Carregando dashboard..." />;

  return (
    <Layout>
      <Header
        title="Dashboard"
        subtitle="Visão geral do seu portfólio"
        action={
          <div className="relative">
            <Button
              onClick={() => setShowActionsMenu(!showActionsMenu)}
              className="flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">Ações</span>
              <ChevronDown className={`w-4 h-4 transition-transform ${showActionsMenu ? 'rotate-180' : ''}`} />
            </Button>

            {showActionsMenu && (
              <>
                {/* Backdrop para fechar o menu */}
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowActionsMenu(false)}
                />

                {/* Menu dropdown */}
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute right-0 mt-2 w-56 bg-card border border-border rounded-lg shadow-lg z-20 overflow-hidden"
                >
                  {acoes.map((acao, index) => {
                    const Icon = acao.icon;
                    return (
                      <button
                        key={index}
                        onClick={() => {
                          acao.onClick();
                          setShowActionsMenu(false);
                        }}
                        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors"
                      >
                        <Icon className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm font-medium">{acao.label}</span>
                      </button>
                    );
                  })}
                </motion.div>
              </>
            )}
          </div>
        }
      />

      <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
        {error && (
          <motion.div
            className="p-3 sm:p-4 bg-destructive/10 border border-destructive/20 rounded-xl text-destructive text-sm"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="flex items-center gap-2">
              {error.includes('Ativando') && (
                <Loader2 className="w-4 h-4 animate-spin" />
              )}
              <span>{error}</span>
            </div>
            {!error.includes('Ativando') && !error.includes('Tentativa') && (
              <Button variant="outline" size="sm" className="ml-2 sm:ml-4 mt-2" onClick={carregarDashboard}>
                Tentar novamente
              </Button>
            )}
          </motion.div>
        )}

        {stats && (
          <>
            {/* Stat Cards - Grid responsivo com animação stagger */}
            <motion.div
              id="dashboard-stats"
              className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              data-testid="dashboard-title"
            >
              <StatCard
                title="Capital Emprestado"
                value={formatarMoeda(stats.total_capital_emprestado)}
                icon={Wallet}
                accent
                index={0}
              />
              <StatCard
                title="Juros a Receber"
                value={formatarMoeda(stats.total_juros_a_receber)}
                icon={TrendingUp}
                index={1}
              />
              <StatCard
                title="Juros Recebidos"
                value={formatarMoeda(stats.total_juros_recebidos)}
                icon={TrendingDown}
                index={2}
              />
              <StatCard
                title="Taxa Inadimplência"
                value={`${stats.taxa_inadimplencia.toFixed(1)}%`}
                icon={AlertTriangle}
                index={3}
              />
              <StatCard
                title="Clientes Ativos"
                value={stats.total_clientes_ativos}
                icon={Users}
                index={4}
              />
              <StatCard
                title="Empréstimos Ativos"
                value={stats.total_emprestimos_ativos}
                icon={Wallet}
                index={5}
              />
              <StatCard
                title="Parcelas em Atraso"
                value={stats.total_parcelas_atrasadas || 0}
                icon={AlertTriangle}
                accent={stats.total_parcelas_atrasadas > 0}
                index={6}
              />
              <StatCard
                title="Clientes em Atraso"
                value={stats.total_clientes_em_atraso || 0}
                icon={Users}
                accent={stats.total_clientes_em_atraso > 0}
                index={7}
              />
            </motion.div>

            {/* 🚨 SEÇÃO DE PAGAMENTOS PENDENTES / ATRASOS */}
            <PagamentosPendentesSection stats={stats} />

            {/* Charts - Grid responsivo */}
            <motion.div
              className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              {/* Evolução Mensal */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5, duration: 0.4 }}
              >
                <Card data-testid="grafico-evolucao">
                  <CardHeader className="p-4 sm:p-6 pb-2 sm:pb-4">
                    <CardTitle className="font-display text-base sm:text-lg">Evolução Mensal</CardTitle>
                  </CardHeader>
                  <CardContent className="p-2 sm:p-6 pt-0">
                    <div className="w-full" style={{ height: '320px', minHeight: '240px' }}>
                      {chartsReady && (
                        <ResponsiveContainer width="99%" height={320}>
                          <AreaChart data={stats.evolucao_mensal || []}>
                            <defs>
                              <linearGradient id="colorValor" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="hsl(160, 84%, 39%)" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="hsl(160, 84%, 39%)" stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(217, 33%, 17%)" />
                            <XAxis dataKey="mes" stroke="hsl(215, 20%, 55%)" fontSize={10} tickLine={false} />
                            <YAxis
                              stroke="hsl(215, 20%, 55%)"
                              fontSize={10}
                              tickLine={false}
                              tickFormatter={(v) => {
                                if (v === 0) return 'R$ 0';
                                if (v >= 1000) return `R$ ${(v / 1000).toFixed(1).replace('.0', '')}k`;
                                return `R$ ${v}`;
                              }}
                              width={60}
                            />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: "hsl(222, 47%, 10%)",
                                border: "1px solid hsl(217, 33%, 20%)",
                                borderRadius: "8px",
                                fontSize: "12px"
                              }}
                              labelStyle={{
                                color: '#f8fafc',
                                fontWeight: 'bold',
                              }}
                              itemStyle={{
                                color: '#38bdf8',
                              }}
                              formatter={(v) => formatarMoeda(v)}
                            />
                            <Area
                              type="monotone"
                              dataKey="valor"
                              name="Capital"
                              stroke="hsl(160, 84%, 39%)"
                              fillOpacity={1}
                              fill="url(#colorValor)"
                            />
                          </AreaChart>
                        </ResponsiveContainer>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Distribuição por Status */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6, duration: 0.4 }}
              >
                <Card data-testid="grafico-status">
                  <CardHeader className="p-4 sm:p-6 pb-2 sm:pb-4">
                    <CardTitle className="font-display text-base sm:text-lg">Distribuição por Status</CardTitle>
                  </CardHeader>
                  <CardContent className="p-2 sm:p-6 pt-0">
                    <div className="w-full" style={{ height: '320px', minHeight: '240px' }}>
                      {chartsReady && (
                        <ResponsiveContainer width="99%" height={320}>
                          <PieChart>
                            <Pie
                              data={(stats.distribuicao_status || []).filter(d => d.value > 0)}
                              cx="50%"
                              cy="50%"
                              labelLine={false}
                              label={({ name, percent }) => window.innerWidth > 640 ? `${name}: ${(percent * 100).toFixed(0)}%` : `${(percent * 100).toFixed(0)}%`}
                              outerRadius={window.innerWidth > 640 ? 100 : 70}
                              fill="#8884d8"
                              dataKey="value"
                              fontSize={10}
                            >
                              {(stats.distribuicao_status || []).map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color || COLORS[index % COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip
                              contentStyle={{
                                backgroundColor: "hsl(222, 47%, 8%)",
                                border: "1px solid hsl(217, 33%, 17%)",
                                borderRadius: "8px",
                                fontSize: "12px",
                                boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.5)"
                              }}
                              itemStyle={{ color: "#e2e8f0" }}
                              formatter={(v) => [`${v} empréstimos`, 'Quantidade']}
                            />
                          </PieChart>
                        </ResponsiveContainer>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Top Clientes */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7, duration: 0.4 }}
              >
                <Card data-testid="grafico-top-clientes">
                  <CardHeader className="p-4 sm:p-6 pb-2 sm:pb-4">
                    <CardTitle className="font-display text-base sm:text-lg">Top 5 Clientes</CardTitle>
                  </CardHeader>
                  <CardContent className="p-2 sm:p-6 pt-0">
                    <div className="w-full" style={{ height: '320px', minHeight: '240px' }}>
                      {chartsReady && (
                        <ResponsiveContainer width="99%" height={320}>
                          <BarChart data={stats.top_clientes || []} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(217, 33%, 17%)" />
                            <XAxis
                              type="number"
                              tickFormatter={(v) => {
                                if (v === 0) return 'R$ 0';
                                if (v >= 1000) return `R$ ${(v / 1000).toFixed(1).replace('.0', '')}k`;
                                return `R$ ${v}`;
                              }}
                              stroke="hsl(215, 20%, 55%)"
                              fontSize={10}
                            />
                            <YAxis type="category" dataKey="nome" width={70} stroke="hsl(215, 20%, 55%)" fontSize={10} tick={{ fontSize: 10 }} />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: "hsl(222, 47%, 10%)",
                                border: "1px solid hsl(217, 33%, 20%)",
                                borderRadius: "8px",
                                fontSize: "12px"
                              }}
                              labelStyle={{
                                color: '#f8fafc',
                                fontWeight: 'bold',
                              }}
                              itemStyle={{
                                color: '#38bdf8',
                              }}
                              formatter={(v) => formatarMoeda(v)}
                            />
                            <Bar dataKey="valor" name="Valor" fill="hsl(280, 65%, 60%)" radius={[0, 4, 4, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Métodos de Cálculo */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8, duration: 0.4 }}
              >
                <Card data-testid="grafico-metodos">
                  <CardHeader className="p-4 sm:p-6 pb-2 sm:pb-4">
                    <CardTitle className="font-display text-base sm:text-lg">Métodos de Cálculo</CardTitle>
                  </CardHeader>
                  <CardContent className="p-2 sm:p-6 pt-0">
                    <div className="w-full" style={{ height: '320px', minHeight: '240px' }}>
                      {chartsReady && (
                        <ResponsiveContainer width="99%" height={320}>
                          <BarChart data={(stats.metodos_calculo || []).filter(m => m.value > 0)}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(217, 33%, 17%)" />
                            <XAxis dataKey="name" stroke="hsl(215, 20%, 55%)" fontSize={10} />
                            <YAxis stroke="hsl(215, 20%, 55%)" fontSize={10} />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: "hsl(222, 47%, 8%)",
                                border: "1px solid hsl(217, 33%, 17%)",
                                borderRadius: "8px",
                                fontSize: "12px"
                              }}
                            />
                            <Bar dataKey="value" name="Quantidade" fill="hsl(160, 84%, 39%)" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </motion.div>

            {/* Próximos Vencimentos */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.9, duration: 0.4 }}
            >
              <Card data-testid="proximos-vencimentos-section">
                <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-4 sm:p-6">
                  <CardTitle className="font-display flex items-center gap-2 text-base sm:text-lg">
                    <Calendar className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
                    Próximos Vencimentos (7 dias)
                  </CardTitle>
                  <Badge variant="secondary" className="w-fit">{stats.proximos_vencimentos?.length || 0} pendentes</Badge>
                </CardHeader>
                <CardContent className="p-4 sm:p-6 pt-0">
                  {stats.proximos_vencimentos?.length === 0 ? (
                    <p className="text-muted-foreground text-sm" data-testid="sem-vencimentos-message">
                      Nenhum vencimento nos próximos 7 dias
                    </p>
                  ) : (
                    <div className="space-y-2 sm:space-y-3" data-testid="vencimentos-table-body">
                      {stats.proximos_vencimentos?.map((venc, index) => (
                        <motion.div
                          key={index}
                          data-testid={`vencimento-row-${index}`}
                          className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors gap-2"
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 1 + index * 0.1 }}
                          whileHover={{ scale: 1.01 }}
                        >
                          <div className="flex items-center gap-3">
                            <motion.div
                              className="w-2 h-2 rounded-full bg-warning flex-shrink-0"
                              animate={{ scale: [1, 1.2, 1] }}
                              transition={{ duration: 2, repeat: Infinity }}
                            />
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-foreground truncate">{venc.cliente_nome}</p>
                              <p className="text-xs text-muted-foreground">
                                Parcela {venc.numero_parcela} • {formatarData(venc.data_vencimento)}
                              </p>
                            </div>
                          </div>
                          <div className="text-left sm:text-right pl-5 sm:pl-0">
                            <p className="text-sm font-semibold text-foreground">{formatarMoeda(venc.valor_total)}</p>
                            <Badge variant="outline" className="text-xs">Pendente</Badge>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </>
        )}
      </div>

      {/* Onboarding Components */}
      {!onboardingLoading && onboarding && (
        <>
          {/* Modal de Boas-vindas */}
          {showWelcome && (
            <OnboardingWelcomeModal
              onStartTour={startTour}
              onSkip={skipOnboarding}
              userName={user?.nome || 'Usuário'}
            />
          )}

          {/* Tour Interativo */}
          {showTour && tourSteps.length > 0 && (
            <OnboardingTour
              steps={tourSteps}
              currentStep={currentStep}
              onNext={nextStep}
              onPrev={prevStep}
              onSkip={skipOnboarding}
              onFinish={finishTour}
            />
          )}

          {/* Checklist - Sempre visível se não completou 100% */}
          {!onboarding.completed && stats && (
            <div className="mt-6">
              <OnboardingChecklist
                tasks={onboarding.tasks}
                progress={onboarding.progress}
                points={onboarding.points}
                totalPoints={onboarding.total_points}
                onTaskClick={updateTask}
                onStartTour={startTour}
              />
            </div>
          )}
        </>
      )}
    </Layout>
  );
};

export default Dashboard;
