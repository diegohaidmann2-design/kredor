import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { aceiteEmprestimoAPI } from '../api/api';
import { dataUrlToBlob } from '../utils/imageCompress';
import SignaturePad from '../components/cadastro-publico/SignaturePad';
import { CheckCircle2, Loader2, ShieldCheck, AlertTriangle, FileSignature, Download, FileText } from 'lucide-react';

const brl = (v) => (Number(v) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const dataBr = (iso) => {
  if (!iso) return '-';
  try { return new Date(iso).toLocaleDateString('pt-BR', { timeZone: 'UTC' }); } catch { return '-'; }
};

const METODO_LABEL = {
  juros_simples: 'Juros Simples',
  juros_compostos: 'Juros Compostos',
  tabela_price: 'Tabela Price',
  sac: 'SAC',
  apenas_juros: 'Somente Juros',
};

const AceiteEmprestimo = () => {
  const { token } = useParams();
  const [carregando, setCarregando] = useState(true);
  const [dados, setDados] = useState(null);
  const [linkInvalido, setLinkInvalido] = useState(false);
  const [jaAceito, setJaAceito] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [erro, setErro] = useState('');
  const [baixandoContrato, setBaixandoContrato] = useState(false);

  const [assinaturaDataUrl, setAssinaturaDataUrl] = useState(null);
  const [confirmouDados, setConfirmouDados] = useState(false);
  const [consentimento, setConsentimento] = useState(false);

  const TURNSTILE_SITE_KEY = process.env.REACT_APP_TURNSTILE_SITE_KEY;
  const turnstileRef = useRef(null);
  const turnstileWidgetId = useRef(null);
  const [turnstileToken, setTurnstileToken] = useState('');

  useEffect(() => {
    if (!token) {
      setLinkInvalido(true);
      setCarregando(false);
      return;
    }
    (async () => {
      try {
        const { data } = await aceiteEmprestimoAPI.info(token);
        setDados(data);
        if (data?.aceite?.status === 'aceito') setJaAceito(true);
      } catch {
        setLinkInvalido(true);
      } finally {
        setCarregando(false);
      }
    })();
  }, [token]);

  useEffect(() => {
    if (!TURNSTILE_SITE_KEY) return undefined;
    let cancelled = false;
    const timer = setInterval(() => {
      if (cancelled) return;
      if (window.turnstile && turnstileRef.current && turnstileWidgetId.current === null) {
        clearInterval(timer);
        turnstileWidgetId.current = window.turnstile.render(turnstileRef.current, {
          sitekey: TURNSTILE_SITE_KEY,
          callback: (t) => { setTurnstileToken(t); setErro(''); },
          'expired-callback': () => setTurnstileToken(''),
          'error-callback': () => setTurnstileToken(''),
        });
      }
    }, 150);
    return () => {
      cancelled = true;
      clearInterval(timer);
      if (turnstileWidgetId.current !== null && window.turnstile) {
        try { window.turnstile.remove(turnstileWidgetId.current); } catch { /* noop */ }
      }
      turnstileWidgetId.current = null;
    };
  }, [TURNSTILE_SITE_KEY, carregando, linkInvalido, enviado, jaAceito]);

  const resetTurnstile = () => {
    setTurnstileToken('');
    if (turnstileWidgetId.current !== null && window.turnstile) {
      try { window.turnstile.reset(turnstileWidgetId.current); } catch { /* noop */ }
    }
  };

  const handleBaixarContrato = async () => {
    if (!token || baixandoContrato) return;
    setBaixandoContrato(true);
    try {
      const res = await aceiteEmprestimoAPI.baixarContratoPdf(token);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Contrato_Assinado_${token}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setErro('Não foi possível gerar o arquivo PDF agora. Tente novamente em instantes.');
    } finally {
      setBaixandoContrato(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErro('');
    if (!confirmouDados) { setErro('Confirme que revisou seus dados e concorda com as condições.'); return; }
    if (!assinaturaDataUrl) { setErro('Assine no campo indicado antes de aceitar.'); return; }
    if (!consentimento) { setErro('Autorize o registro do aceite e da assinatura.'); return; }
    if (TURNSTILE_SITE_KEY && !turnstileToken) { setErro('Confirme que você não é um robô.'); return; }

    setEnviando(true);
    try {
      const fd = new FormData();
      fd.append('confirmou_dados', 'true');
      fd.append('consentimento', consentimento ? 'true' : 'false');
      if (turnstileToken) fd.append('turnstile_token', turnstileToken);
      fd.append('assinatura', dataUrlToBlob(assinaturaDataUrl), 'assinatura.png');
      await aceiteEmprestimoAPI.confirmar(token, fd);
      setEnviado(true);
    } catch (err) {
      setErro(err.response?.data?.detail || 'Não foi possível registrar o aceite. Tente novamente.');
      resetTurnstile();
    } finally {
      setEnviando(false);
    }
  };

  if (carregando) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  if (linkInvalido) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-4">
        <div className="max-w-md text-center" data-testid="aceite-link-invalido">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-foreground mb-2">Link inválido ou expirado</h1>
          <p className="text-muted-foreground">Peça um novo link de aceite ao responsável.</p>
        </div>
      </div>
    );
  }

  if (enviado || jaAceito) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-4 py-8">
        <div className="max-w-md w-full text-center bg-card border border-border rounded-2xl p-6 md:p-8 shadow-sm" data-testid="aceite-concluido">
          <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-10 h-10 text-emerald-500" />
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">
            {enviado ? 'Aceite registrado com sucesso! 🎉' : 'Empréstimo já aceito'}
          </h1>
          <p className="text-muted-foreground text-sm mb-6">
            {enviado
              ? `Obrigado! ${dados?.empresa || 'A empresa'} recebeu sua confirmação e assinatura digital.`
              : 'Este empréstimo já foi formalizado e assinado digitalmente com sucesso.'}
          </p>

          <div className="p-4 rounded-xl bg-muted/40 border border-border mb-6 text-left">
            <div className="flex items-center gap-2 mb-2 text-sm font-semibold text-foreground">
              <FileText className="w-4 h-4 text-primary" />
              <span>Contrato de Mútuo Assinado</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              O documento contém todas as condições contratuais, tabela de parcelas, sua assinatura digitalizada e o carimbo de auditoria eletrônica em conformidade com a MP 2.200-2/2001 e a LGPD.
            </p>
          </div>

          <button
            onClick={handleBaixarContrato}
            disabled={baixandoContrato}
            className="w-full inline-flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl bg-primary text-primary-foreground font-semibold shadow hover:opacity-95 transition-all disabled:opacity-60"
            data-testid="btn-baixar-contrato-pdf"
          >
            {baixandoContrato ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Gerando PDF do Contrato...</span>
              </>
            ) : (
              <>
                <Download className="w-5 h-5" />
                <span>Baixar Contrato Assinado (PDF)</span>
              </>
            )}
          </button>

          {erro && (
            <div className="mt-4 flex items-start gap-2 p-3 rounded-lg bg-red-500/10 text-red-500 text-xs text-left">
              <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" /> {erro}
            </div>
          )}

          <p className="mt-6 flex items-center justify-center gap-1.5 text-xs text-muted-foreground">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" /> Registro eletrônico com carimbo de tempo seguro.
          </p>
        </div>
      </div>
    );
  }

  const emp = dados.emprestimo;
  const cli = dados.cliente;
  const end = cli.endereco || {};
  const taxa = emp.periodicidade === 'semanal' ? emp.taxa_juros_semanal : emp.taxa_juros_mensal;
  const prazo = emp.periodicidade === 'semanal' ? emp.prazo_semanas : emp.prazo_meses;
  const periodoLabel = emp.periodicidade === 'semanal' ? 'semanal' : 'mensal';

  const linha = "flex justify-between border-b border-border py-1.5 text-sm";

  return (
    <div className="min-h-screen bg-background py-8 px-4">
      <div className="max-w-xl mx-auto">
        <div className="text-center mb-6">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-emerald-600 flex items-center justify-center mx-auto mb-3">
            <FileSignature className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-foreground" data-testid="aceite-empresa">{dados.empresa}</h1>
          <p className="text-muted-foreground text-sm mt-1">Revise seus dados e as condições e assine para aceitar</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" data-testid="form-aceite">
          {/* Dados do cliente */}
          <div className="bg-card border border-border rounded-2xl p-5" data-testid="aceite-dados-cliente">
            <h2 className="text-base font-semibold text-foreground mb-3">Seus dados</h2>
            <div className={linha}><span className="text-muted-foreground">Nome</span><span className="font-medium text-foreground text-right">{cli.nome || '-'}</span></div>
            {cli.cpf_cnpj && <div className={linha}><span className="text-muted-foreground">CPF/CNPJ</span><span className="font-medium text-foreground">{cli.cpf_cnpj}</span></div>}
            <div className={linha}><span className="text-muted-foreground">Telefone</span><span className="font-medium text-foreground">{cli.telefone || '-'}</span></div>
            {cli.email && <div className={linha}><span className="text-muted-foreground">E-mail</span><span className="font-medium text-foreground text-right break-all">{cli.email}</span></div>}
            {(end.rua || end.cidade) && (
              <div className={linha}>
                <span className="text-muted-foreground">Endereço</span>
                <span className="font-medium text-foreground text-right">
                  {[end.rua, end.numero].filter(Boolean).join(', ')}{end.bairro ? ` - ${end.bairro}` : ''}{end.cidade ? `, ${end.cidade}/${end.estado}` : ''}
                </span>
              </div>
            )}
          </div>

          {/* Condições do empréstimo */}
          <div className="bg-card border border-border rounded-2xl p-5" data-testid="aceite-condicoes">
            <h2 className="text-base font-semibold text-foreground mb-3">Condições do empréstimo</h2>
            <div className={linha}><span className="text-muted-foreground">Valor principal</span><span className="font-semibold text-foreground" data-testid="aceite-valor-principal">{brl(emp.valor_principal)}</span></div>
            {!emp.sem_prazo && (
              <div className={linha}><span className="text-muted-foreground">Total com juros</span><span className="font-semibold text-emerald-600" data-testid="aceite-total">{brl(emp.valor_total_com_juros)}</span></div>
            )}
            {taxa != null && <div className={linha}><span className="text-muted-foreground">Taxa de juros ({periodoLabel})</span><span className="font-medium text-foreground">{taxa}%</span></div>}
            {!emp.sem_prazo && prazo != null && <div className={linha}><span className="text-muted-foreground">Prazo</span><span className="font-medium text-foreground">{prazo} {emp.periodicidade === 'semanal' ? 'semanas' : 'meses'}</span></div>}
            {emp.sem_prazo && <div className={linha}><span className="text-muted-foreground">Modalidade</span><span className="font-medium text-foreground">Empréstimo aberto ({periodoLabel})</span></div>}
            <div className={linha}><span className="text-muted-foreground">Cálculo</span><span className="font-medium text-foreground">{METODO_LABEL[emp.metodo_calculo] || emp.metodo_calculo}</span></div>
            <div className={linha}><span className="text-muted-foreground">Início</span><span className="font-medium text-foreground">{dataBr(emp.data_inicio)}</span></div>
          </div>

          {/* Parcelas */}
          {dados.parcelas?.length > 0 && (
            <div className="bg-card border border-border rounded-2xl p-5" data-testid="aceite-parcelas">
              <h2 className="text-base font-semibold text-foreground mb-3">Parcelas ({dados.parcelas.length})</h2>
              <div className="max-h-64 overflow-y-auto rounded-lg border border-border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 sticky top-0">
                    <tr className="text-muted-foreground">
                      <th className="text-left px-3 py-2 font-medium">#</th>
                      <th className="text-left px-3 py-2 font-medium">Vencimento</th>
                      <th className="text-right px-3 py-2 font-medium">Valor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dados.parcelas.map((p) => (
                      <tr key={p.numero_parcela} className="border-t border-border">
                        <td className="px-3 py-2 text-foreground">{p.numero_parcela}</td>
                        <td className="px-3 py-2 text-foreground">{dataBr(p.data_vencimento)}</td>
                        <td className="px-3 py-2 text-right font-medium text-foreground">{brl(p.valor_total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Assinatura */}
          <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
            <SignaturePad value={assinaturaDataUrl} onChange={setAssinaturaDataUrl} testId="aceite-assinatura" />

            <label className="flex items-start gap-2 p-3 rounded-lg border border-border bg-muted/20 cursor-pointer" data-testid="aceite-confirmar-label">
              <input type="checkbox" checked={confirmouDados} onChange={(e) => { setConfirmouDados(e.target.checked); setErro(''); }} className="mt-0.5 w-4 h-4" data-testid="input-confirmou-dados" />
              <span className="text-xs text-muted-foreground leading-snug">Revisei meus dados e as condições acima e concordo com o empréstimo.</span>
            </label>

            <label className="flex items-start gap-2 p-3 rounded-lg border border-border bg-muted/20 cursor-pointer" data-testid="aceite-consentimento-label">
              <input type="checkbox" checked={consentimento} onChange={(e) => { setConsentimento(e.target.checked); setErro(''); }} className="mt-0.5 w-4 h-4" data-testid="input-aceite-consentimento" />
              <span className="text-xs text-muted-foreground leading-snug">Autorizo o registro do meu aceite e da minha assinatura para fins deste empréstimo (termo {dados.aceite?.versao_termo}).</span>
            </label>
          </div>

          {erro && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 text-red-500 text-sm" data-testid="aceite-erro">
              <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" /> {erro}
            </div>
          )}

          {TURNSTILE_SITE_KEY && (
            <div className="flex justify-center" data-testid="aceite-turnstile">
              <div ref={turnstileRef} />
            </div>
          )}

          <button
            type="submit"
            disabled={enviando}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-primary text-primary-foreground font-semibold hover:opacity-90 transition-opacity disabled:opacity-60"
            data-testid="btn-aceitar"
          >
            {enviando ? <><Loader2 className="w-4 h-4 animate-spin" /> Registrando...</> : 'Aceitar e assinar'}
          </button>

          <p className="flex items-center justify-center gap-1.5 text-xs text-muted-foreground">
            <ShieldCheck className="w-3.5 h-3.5 text-primary" /> Seu aceite é registrado com segurança.
          </p>
        </form>
      </div>
    </div>
  );
};

export default AceiteEmprestimo;
