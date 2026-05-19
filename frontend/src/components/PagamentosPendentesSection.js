import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import {
  AlertTriangle, Clock, CalendarDays, ArrowUpRight, MessageCircle, PhoneCall, TrendingUp
} from 'lucide-react';
import { formatarMoeda, formatarData } from '../utils/formatters';
import { whatsappAPI } from '../api/api';
import { useModal } from './Modal';

/**
 * Seção do Dashboard focada em PAGAMENTOS PENDENTES / EM ATRASO.
 * Inclui:
 *  - Cards: A Receber Hoje / Semana / Mês / Recebido este mês / Valor em Atraso
 *  - Próximo recebimento destacado
 *  - Aging dos atrasos (gráfico)
 *  - Top inadimplentes (lista com ação de cobrar via WhatsApp)
 */
const PagamentosPendentesSection = ({ stats }) => {
  const navigate = useNavigate();
  const modal = useModal();
  const [cobrando, setCobrando] = React.useState(null);

  if (!stats) return null;

  const valorEmAtraso = stats.valor_em_atraso || 0;
  const aReceberHoje = stats.a_receber_hoje || 0;
  const aReceberSemana = stats.a_receber_semana || 0;
  const aReceberMes = stats.a_receber_mes || 0;
  const recebidoMes = stats.recebido_mes_atual || 0;
  const proximo = stats.proximo_recebimento;
  const aging = stats.aging_atrasos || [];
  const topInadimplentes = stats.top_inadimplentes || [];

  const handleCobrar = async (cliente, parcelaIds = null) => {
    setCobrando(cliente.cliente_id);
    try {
      // Se passou IDs específicos, usa endpoint em massa
      // Por simplicidade aqui (no dashboard), navegamos para /pagamentos com filtro
      // (cobrança em massa é feita lá)
      navigate(`/pagamentos?cliente=${encodeURIComponent(cliente.cliente_nome || '')}`);
    } catch (err) {
      modal.error('Erro', err.response?.data?.detail || 'Falha ao cobrar.');
    } finally {
      setCobrando(null);
    }
  };

  const totalAging = aging.reduce((sum, a) => sum + (a.valor || 0), 0);

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* CARDS DE RECEBÍVEIS / ATRASO */}
      <motion.div
        className="grid grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.4 }}
      >
        {/* Valor em atraso - destaque vermelho */}
        <Card
          data-testid="card-valor-em-atraso"
          className={`relative overflow-hidden border-l-4 ${valorEmAtraso > 0 ? 'border-l-red-500 bg-gradient-to-br from-red-500/5 to-red-500/0' : 'border-l-muted'}`}
        >
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-start justify-between">
              <div className="min-w-0">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Valor em Atraso
                </p>
                <p className={`text-lg sm:text-2xl font-display font-bold mt-1 truncate ${valorEmAtraso > 0 ? 'text-red-500' : 'text-foreground'}`}>
                  {formatarMoeda(valorEmAtraso)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {stats.total_parcelas_atrasadas || 0} parcela{(stats.total_parcelas_atrasadas || 0) === 1 ? '' : 's'} • {stats.total_clientes_em_atraso || 0} cliente{(stats.total_clientes_em_atraso || 0) === 1 ? '' : 's'}
                </p>
              </div>
              <div className={`p-2 rounded-lg ${valorEmAtraso > 0 ? 'bg-red-500/15 text-red-500' : 'bg-muted text-muted-foreground'}`}>
                <AlertTriangle className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* A receber hoje */}
        <Card
          data-testid="card-receber-hoje"
          className="border-l-4 border-l-amber-500 bg-gradient-to-br from-amber-500/5 to-amber-500/0"
        >
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-start justify-between">
              <div className="min-w-0">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  A Receber Hoje
                </p>
                <p className="text-lg sm:text-2xl font-display font-bold text-amber-500 mt-1 truncate">
                  {formatarMoeda(aReceberHoje)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">Vence hoje</p>
              </div>
              <div className="p-2 rounded-lg bg-amber-500/15 text-amber-500">
                <Clock className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* A receber 7d */}
        <Card data-testid="card-receber-semana" className="border-l-4 border-l-sky-500">
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-start justify-between">
              <div className="min-w-0">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  A Receber 7 dias
                </p>
                <p className="text-lg sm:text-2xl font-display font-bold text-sky-500 mt-1 truncate">
                  {formatarMoeda(aReceberSemana)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">Próximos 7 dias</p>
              </div>
              <div className="p-2 rounded-lg bg-sky-500/15 text-sky-500">
                <CalendarDays className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* A receber este mês */}
        <Card data-testid="card-receber-mes" className="border-l-4 border-l-violet-500">
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-start justify-between">
              <div className="min-w-0">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  A Receber Este Mês
                </p>
                <p className="text-lg sm:text-2xl font-display font-bold text-violet-500 mt-1 truncate">
                  {formatarMoeda(aReceberMes)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">Até fim do mês</p>
              </div>
              <div className="p-2 rounded-lg bg-violet-500/15 text-violet-500">
                <CalendarDays className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recebido no mês */}
        <Card data-testid="card-recebido-mes" className="border-l-4 border-l-emerald-500 bg-gradient-to-br from-emerald-500/5 to-emerald-500/0">
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-start justify-between">
              <div className="min-w-0">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Recebido no Mês
                </p>
                <p className="text-lg sm:text-2xl font-display font-bold text-emerald-500 mt-1 truncate">
                  {formatarMoeda(recebidoMes)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">Pagamentos do mês</p>
              </div>
              <div className="p-2 rounded-lg bg-emerald-500/15 text-emerald-500">
                <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* PRÓXIMO RECEBIMENTO + AGING */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Próximo Recebimento */}
        {proximo && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
          >
            <Card
              data-testid="card-proximo-recebimento"
              className="h-full border-primary/30 bg-gradient-to-br from-primary/5 via-primary/3 to-transparent"
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2 text-primary">
                  <ArrowUpRight className="w-4 h-4" />
                  Próximo Recebimento
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl sm:text-3xl font-display font-bold text-foreground mb-1">
                  {formatarMoeda(proximo.valor || 0)}
                </p>
                <p className="text-sm text-foreground mb-1 truncate">{proximo.cliente_nome}</p>
                <p className="text-xs text-muted-foreground">
                  Parcela {proximo.numero_parcela} • {formatarData(proximo.data_vencimento)}
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  className="mt-3 w-full"
                  onClick={() => navigate('/pagamentos')}
                  data-testid="btn-ver-pagamentos"
                >
                  Ver pagamentos
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Aging dos Atrasos */}
        <motion.div
          className={proximo ? 'lg:col-span-2' : 'lg:col-span-3'}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.25 }}
        >
          <Card data-testid="card-aging-atrasos" className="h-full">
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                Aging dos Atrasos
              </CardTitle>
              <Badge variant="outline" className="text-xs">
                {formatarMoeda(totalAging)} total
              </Badge>
            </CardHeader>
            <CardContent>
              {totalAging > 0 ? (
                <div style={{ width: '100%', height: 200 }}>
                  <ResponsiveContainer width="99%" height="100%">
                    <BarChart data={aging} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(217, 33%, 17%)" />
                      <XAxis dataKey="faixa" stroke="hsl(215, 20%, 55%)" fontSize={11} />
                      <YAxis
                        stroke="hsl(215, 20%, 55%)"
                        fontSize={10}
                        tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                        width={40}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(222, 47%, 8%)',
                          border: '1px solid hsl(217, 33%, 17%)',
                          borderRadius: 8,
                          fontSize: 12,
                        }}
                        formatter={(v, name, item) => [
                          `${formatarMoeda(v)} (${item.payload.quantidade} parcelas)`,
                          'Valor em atraso'
                        ]}
                      />
                      <Bar dataKey="valor" radius={[4, 4, 0, 0]}>
                        {aging.map((entry, idx) => (
                          <Cell key={idx} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[200px] flex items-center justify-center text-sm text-muted-foreground">
                  Nenhuma parcela em atraso 🎉
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* TOP INADIMPLENTES */}
      {topInadimplentes.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card data-testid="card-top-inadimplentes" className="border-red-500/20">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                Top Inadimplentes
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate('/pagamentos?filtro=atrasado')}
                data-testid="btn-ver-todos-inadimplentes"
              >
                Ver todos
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {topInadimplentes.slice(0, 5).map((c, idx) => (
                  <motion.div
                    key={c.cliente_id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.35 + idx * 0.05 }}
                    className="flex items-center justify-between gap-3 p-3 rounded-lg bg-red-500/5 hover:bg-red-500/10 transition-colors border border-red-500/10"
                    data-testid={`inadimplente-row-${idx}`}
                  >
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div className="h-9 w-9 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0">
                        <span className="text-red-500 font-bold text-sm">
                          {(c.cliente_nome || '?').charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-foreground truncate">
                          {c.cliente_nome}
                        </p>
                        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground mt-0.5">
                          <span>{c.parcelas_atrasadas} parcela{c.parcelas_atrasadas === 1 ? '' : 's'}</span>
                          <span>•</span>
                          <span className="text-red-500 font-medium">{c.dias_max_atraso}d atraso</span>
                          {c.cliente_telefone && (
                            <>
                              <span>•</span>
                              <span className="flex items-center gap-1">
                                <PhoneCall className="w-3 h-3" /> {c.cliente_telefone}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      <div className="text-right">
                        <p className="text-sm font-bold text-red-500">{formatarMoeda(c.valor_devido)}</p>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-green-500/30 text-green-600 hover:bg-green-500/10 hover:text-green-600"
                        onClick={() => handleCobrar(c)}
                        disabled={cobrando === c.cliente_id}
                        data-testid={`btn-cobrar-${c.cliente_id}`}
                      >
                        <MessageCircle className="w-4 h-4 mr-1" />
                        <span className="hidden sm:inline">Cobrar</span>
                      </Button>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
};

export default PagamentosPendentesSection;
