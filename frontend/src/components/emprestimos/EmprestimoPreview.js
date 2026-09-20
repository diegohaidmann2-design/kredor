import React from 'react';
import {
    User,
    Wallet,
    Percent,
    CalendarClock,
    TrendingUp,
    ListOrdered,
    Info,
    Loader2,
    Calculator
} from 'lucide-react';
import { emprestimosAPI } from '../../api/api';

const brl = (v) =>
    (Number.isFinite(v) ? v : 0).toLocaleString('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    });

const formatarData = (iso) => {
    if (!iso) return '—';
    try {
        return new Date(iso).toLocaleDateString('pt-BR');
    } catch (e) {
        return '—';
    }
};

const metodoLabel = {
    tabela_price: 'Tabela Price',
    sac: 'SAC',
    juros_simples: 'Juros Simples',
    juros_compostos: 'Juros Compostos',
    apenas_juros: 'Apenas Juros'
};

/**
 * Painel de Preview/Simulação em tempo real.
 * REUTILIZA a mesma lógica financeira do backend chamando /emprestimos/simular,
 * garantindo Preview === Empréstimo realmente criado.
 * Para empréstimo aberto (sem_prazo), espelha a fórmula do backend:
 * juros_periodo = principal * (taxa/100).
 */
const EmprestimoPreview = ({ formData, clientes = [] }) => {
    const [sim, setSim] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [erro, setErro] = React.useState('');

    const cliente = clientes.find((c) => c.id === formData.cliente_id);
    const PERIOD = {
        mensal:    { taxa: 'taxa_juros_mensal',    prazo: 'prazo_meses',     unidade: 'mês' },
        semanal:   { taxa: 'taxa_juros_semanal',   prazo: 'prazo_semanas',   unidade: 'semana' },
        quinzenal: { taxa: 'taxa_juros_quinzenal', prazo: 'prazo_quinzenas', unidade: 'quinzena' },
    };
    const per = PERIOD[formData.periodicidade] || PERIOD.mensal;
    const unidade = per.unidade;
    const semPrazo = !!formData.sem_prazo;

    const principal = parseFloat(formData.valor_principal) || 0;
    const taxa = parseFloat(formData[per.taxa]) || 0;
    const prazo = parseInt(formData[per.prazo], 10) || 0;

    const podeSimular = principal > 0 && taxa > 0 && (semPrazo || prazo > 0);

    React.useEffect(() => {
        // Empréstimo aberto: preview local (mesma fórmula do backend), sem chamar /simular
        if (semPrazo || !podeSimular) {
            setSim(null);
            setErro('');
            setLoading(false);
            return undefined;
        }

        let ativo = true;
        setLoading(true);
        const timer = setTimeout(async () => {
            try {
                const payload = {
                    valor_principal: principal,
                    metodo_calculo: formData.metodo_calculo,
                    periodo_carencia_meses: parseInt(formData.periodo_carencia_meses || 0, 10),
                    taxa_multa_atraso: parseFloat(formData.taxa_multa_atraso) || 0,
                    taxa_juros_mora_diario: parseFloat(formData.taxa_juros_mora_diario) || 0,
                    periodicidade: formData.periodicidade,
                    dia_vencimento: formData.dia_vencimento ? parseInt(formData.dia_vencimento, 10) : null,
                    data_inicio: formData.data_inicio
                        ? new Date(formData.data_inicio + 'T12:00:00').toISOString()
                        : null
                };
                if (semPrazo) {
                    payload[per.taxa] = taxa;
                } else {
                    payload[per.taxa] = taxa;
                    payload[per.prazo] = prazo;
                }
                const res = await emprestimosAPI.simular(payload);
                if (ativo) {
                    setSim(res.data);
                    setErro('');
                }
            } catch (e) {
                if (ativo) {
                    setSim(null);
                    setErro('Não foi possível simular com os dados atuais.');
                }
            } finally {
                if (ativo) setLoading(false);
            }
        }, 400);

        return () => {
            ativo = false;
            clearTimeout(timer);
        };
    }, [
        semPrazo,
        podeSimular,
        principal,
        taxa,
        prazo,
        formData.periodicidade,
        formData.metodo_calculo,
        formData.periodo_carencia_meses,
        formData.dia_vencimento,
        formData.data_inicio,
        formData.taxa_multa_atraso,
        formData.taxa_juros_mora_diario
    ]);

    // Valores derivados
    const jurosAberto = principal * (taxa / 100);
    const totalComJuros = semPrazo ? null : sim?.valor_total_com_juros ?? null;
    const totalJuros = semPrazo ? jurosAberto : sim?.valor_total_juros ?? null;
    const parcelas = sim?.parcelas || [];
    const proximoVenc = parcelas.length ? parcelas[0].data_vencimento : null;
    const numParcelas = parcelas.length;
    const parcelasIguais =
        numParcelas > 0 &&
        parcelas.every((p) => Math.abs(p.valor_total - parcelas[0].valor_total) < 0.01);
    const valorParcela = parcelasIguais ? parcelas[0].valor_total : null;

    const temDadosBasicos = principal > 0 || !!cliente;
    const mostrarResultado = semPrazo ? podeSimular : !!sim;

    const Linha = ({ icon: Icon, label, children, destaque }) => (
        <div
            className={`flex items-start justify-between gap-3 py-2.5 ${
                destaque ? '' : 'border-b border-border/60'
            }`}
        >
            <span className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
                <Icon className="w-3.5 h-3.5" />
                {label}
            </span>
            <span
                className={`text-right ${
                    destaque ? 'text-lg font-bold text-primary' : 'text-sm font-semibold text-foreground'
                }`}
            >
                {children}
            </span>
        </div>
    );

    return (
        <div
            data-testid="emprestimo-preview"
            className="lg:sticky lg:top-0 rounded-xl border border-border bg-muted/30 p-5 h-fit"
        >
            <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-primary/15 flex items-center justify-center">
                    <Calculator className="w-4 h-4 text-primary" />
                </div>
                <div>
                    <h3 className="text-sm font-bold text-foreground leading-tight">Preview / Simulação</h3>
                    <p className="text-[11px] text-muted-foreground">Atualiza em tempo real</p>
                </div>
                {loading && <Loader2 className="w-4 h-4 text-primary animate-spin ml-auto" data-testid="preview-loading" />}
            </div>

            {!temDadosBasicos ? (
                <div className="flex flex-col items-center justify-center text-center py-10 text-muted-foreground">
                    <Info className="w-8 h-8 mb-3 opacity-50" />
                    <p className="text-sm">Preencha os dados ao lado para visualizar a simulação.</p>
                </div>
            ) : (
                <div className="space-y-1">
                    <Linha icon={User} label="Cliente">
                        <span data-testid="preview-cliente" className="max-w-[180px] truncate inline-block">
                            {cliente ? cliente.nome : '—'}
                        </span>
                    </Linha>

                    <Linha icon={Wallet} label="Capital">
                        <span data-testid="preview-capital">{brl(principal)}</span>
                    </Linha>

                    <Linha icon={Percent} label="Juros">
                        <span data-testid="preview-taxa">
                            {taxa > 0 ? `${taxa}% ao ${unidade}` : '—'}
                        </span>
                    </Linha>

                    {semPrazo ? (
                        <>
                            <Linha icon={TrendingUp} label={`Juros por ${unidade}`}>
                                <span data-testid="preview-juros-periodo">
                                    {podeSimular ? brl(jurosAberto) : '—'}
                                </span>
                            </Linha>
                            <div className="mt-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-xs text-blue-700 dark:text-blue-300">
                                Empréstimo aberto: o cliente paga <strong>{brl(jurosAberto)}</strong> de juros
                                por {unidade}. O capital de <strong>{brl(principal)}</strong> é quitado no final.
                            </div>
                        </>
                    ) : (
                        <>
                            <Linha icon={ListOrdered} label="Parcelas">
                                <span data-testid="preview-parcelas">
                                    {mostrarResultado ? `${numParcelas}x` : '—'}
                                    {mostrarResultado && valorParcela ? ` de ${brl(valorParcela)}` : ''}
                                    {mostrarResultado && !valorParcela ? ' (variável)' : ''}
                                </span>
                            </Linha>

                            <Linha icon={CalendarClock} label="Próx. vencimento">
                                <span data-testid="preview-vencimento">
                                    {mostrarResultado ? formatarData(proximoVenc) : '—'}
                                </span>
                            </Linha>

                            <Linha icon={TrendingUp} label="Total de juros">
                                <span data-testid="preview-total-juros">
                                    {mostrarResultado ? brl(totalJuros) : '—'}
                                </span>
                            </Linha>
                        </>
                    )}

                    {/* Total estimado em destaque */}
                    {!semPrazo && (
                        <div className="mt-4 rounded-xl bg-primary/10 border border-primary/30 p-4">
                            <Linha icon={Wallet} label="Total estimado" destaque>
                                <span data-testid="preview-total">
                                    {mostrarResultado ? brl(totalComJuros) : '—'}
                                </span>
                            </Linha>
                        </div>
                    )}

                    {/* Resumo */}
                    {mostrarResultado && (
                        <div className="mt-4 rounded-lg bg-background/60 border border-border p-3 space-y-1.5">
                            <p className="text-[11px] uppercase tracking-wide text-muted-foreground mb-2">Resumo</p>
                            <div className="flex justify-between text-xs">
                                <span className="text-muted-foreground">Capital</span>
                                <span className="text-foreground font-medium">{brl(principal)}</span>
                            </div>
                            <div className="flex justify-between text-xs">
                                <span className="text-muted-foreground">
                                    Juros{semPrazo ? ` (por ${unidade})` : ''}
                                </span>
                                <span className="text-amber-500 font-medium">{brl(totalJuros)}</span>
                            </div>
                            {!semPrazo && (
                                <div className="flex justify-between text-xs pt-1.5 border-t border-border">
                                    <span className="text-muted-foreground">Total</span>
                                    <span className="text-primary font-bold">{brl(totalComJuros)}</span>
                                </div>
                            )}
                            <div className="flex justify-between text-[11px] text-muted-foreground pt-1">
                                <span>Método</span>
                                <span>{metodoLabel[formData.metodo_calculo] || formData.metodo_calculo}</span>
                            </div>
                        </div>
                    )}

                    {erro && (
                        <p data-testid="preview-erro" className="mt-3 text-xs text-red-500">
                            {erro}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
};

export default EmprestimoPreview;
