import React, { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, FileText, Loader2, MessageCircle } from 'lucide-react';
import { useModal } from '../Modal';
import { emprestimosAPI, pagamentosAPI } from '../../api/api';
import { formatarMoeda, formatarData } from '../../utils/formatters';

// A listagem renderiza a tabela (desktop) e os cards (mobile) ao mesmo tempo, um escondido por CSS.
// A variante entra nos data-testid para os dois não colidirem.

const baixarPdf = (conteudo, nomeArquivo) => {
  const url = window.URL.createObjectURL(new Blob([conteudo], { type: 'application/pdf' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = nomeArquivo;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

/** Baixa o recibo (PDF) de um pagamento de parcela. Erros sobem para quem chamou tratar. */
export const baixarReciboPagamento = async (pagamentoId) => {
  const { data } = await pagamentosAPI.recibo(pagamentoId);
  baixarPdf(data, `recibo_pagamento_${pagamentoId.substring(0, 8)}.pdf`);
};

const textoReciboWhatsapp = (pagamento, clienteNome, emprestimo) => {
  const linhas = [
    pagamento.status_parcela_apos === 'parcial' ? '🧾 *RECIBO DE PAGAMENTO PARCIAL*' : '🧾 *RECIBO DE PAGAMENTO*',
    '',
    `Olá ${clienteNome}! Confirmamos o recebimento do seu pagamento.`,
    '',
    `📄 Contrato: #${emprestimo.id.substring(0, 8).toUpperCase()}`,
  ];
  if (pagamento.numero_parcela) {
    linhas.push(`🔢 Parcela: ${pagamento.numero_parcela}${pagamento.total_parcelas ? `/${pagamento.total_parcelas}` : ''}`);
  }
  linhas.push(`📅 Data: ${formatarData(pagamento.data_pagamento)}`);
  linhas.push(`💵 Valor pago: ${formatarMoeda(pagamento.valor_pago || 0)}`);
  if (pagamento.saldo_parcela_restante != null) {
    linhas.push(`⏳ Ficou faltando nesta parcela: ${formatarMoeda(pagamento.saldo_parcela_restante)}`);
  }
  if (pagamento.saldo_emprestimo_restante != null) {
    linhas.push(`💰 Saldo devedor do empréstimo: ${formatarMoeda(pagamento.saldo_emprestimo_restante)}`);
  }
  linhas.push('', 'Obrigado! 🤝');
  return linhas.join('\n');
};

/**
 * Quanto já foi recebido e quanto falta, direto na linha/card do empréstimo.
 * Os totais vêm prontos do backend (GET /emprestimos): total_recebido e saldo_restante; no
 * empréstimo aberto, juros_pagos e juros_em_aberto (pagamento imputado primeiro nos juros).
 */
export const ResumoPagamentos = ({ emprestimo, aberto, onToggle, variante = 'tabela' }) => {
  const recebido = emprestimo.total_recebido || 0;
  const falta = emprestimo.saldo_restante || 0;
  const jurosEmAberto = emprestimo.juros_em_aberto || 0;
  const qtd = emprestimo.qtd_pagamentos || 0;
  const parciais = emprestimo.parcelas_com_pagamento_parcial || 0;
  const total = recebido + falta;
  const percentual = total > 0 ? Math.min(100, Math.round((recebido / total) * 100)) : 0;

  return (
    <div className="mt-1 space-y-1 text-xs" data-testid={`resumo-pagamentos-${variante}-${emprestimo.id}`}>
      {emprestimo.sem_prazo ? (
        // Aberto: o capital só volta por amortização; o que o credor acompanha é o histórico de juros.
        <>
          <div className="flex flex-wrap items-center gap-x-1" data-testid={`resumo-juros-${variante}-${emprestimo.id}`}>
            <span className="text-emerald-600">Juros pagos {formatarMoeda(emprestimo.juros_pagos || 0)}</span>
            <span className={jurosEmAberto > 0 ? 'text-amber-600' : 'text-muted-foreground'}>
              · Juros em aberto {formatarMoeda(jurosEmAberto)}
            </span>
          </div>
          <div className="text-muted-foreground">Capital a devolver {formatarMoeda(emprestimo.valor_principal || 0)}</div>
        </>
      ) : (
        <div className="flex flex-wrap items-center gap-x-1">
          <span className="text-emerald-600">Recebido {formatarMoeda(recebido)}</span>
          <span className={falta > 0 ? 'text-amber-600' : 'text-emerald-600'}>
            {falta > 0 ? `· Falta ${formatarMoeda(falta)}` : '· Nada em aberto'}
          </span>
        </div>
      )}
      {/* Em empréstimo aberto o total não é fixo, então a barra de progresso não tem sentido. */}
      {!emprestimo.sem_prazo && total > 0 && (
        <div className="h-1.5 w-full max-w-[180px] rounded-full bg-muted overflow-hidden" title={`${percentual}% recebido`}>
          <div className="h-full bg-emerald-500" style={{ width: `${percentual}%` }} />
        </div>
      )}
      {qtd > 0 && (
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={aberto}
          className="inline-flex items-center gap-1 text-primary hover:underline"
          data-testid={`btn-historico-pagamentos-${variante}-${emprestimo.id}`}
        >
          {aberto ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          {qtd} {qtd === 1 ? 'pagamento' : 'pagamentos'}
          {parciais > 0 && ` · ${parciais} ${parciais === 1 ? 'parcela parcial' : 'parcelas parciais'}`}
        </button>
      )}
    </div>
  );
};

/** Lista os pagamentos recebidos do empréstimo, cada um com recibo em PDF e envio por WhatsApp. */
const PagamentosDoEmprestimo = ({ emprestimo, clienteNome, clienteTelefone, variante = 'tabela' }) => {
  const modal = useModal();
  const [pagamentos, setPagamentos] = useState(null);
  const [erro, setErro] = useState(null);
  const [processando, setProcessando] = useState(null);

  // qtd_pagamentos na dependência: um pagamento novo recarrega a lista já aberta.
  useEffect(() => {
    let ativo = true;
    setErro(null);
    pagamentosAPI.listar({ emprestimo_id: emprestimo.id })
      .then(({ data }) => {
        if (ativo) setPagamentos((data || []).filter((p) => p.tipo !== 'incorporacao_juros'));
      })
      .catch((err) => {
        if (ativo) setErro(err.response?.data?.detail || 'Não foi possível carregar os pagamentos deste empréstimo.');
      });
    return () => { ativo = false; };
  }, [emprestimo.id, emprestimo.qtd_pagamentos]);

  const ehAmortizacao = (pagamento) => pagamento.tipo === 'amortizacao';

  const baixarRecibo = async (pagamento) => {
    setProcessando(pagamento.id);
    try {
      if (ehAmortizacao(pagamento)) {
        const { data } = await emprestimosAPI.reciboAmortizacao(emprestimo.id, pagamento.id);
        baixarPdf(data, `recibo_amortizacao_${pagamento.id.substring(0, 8)}.pdf`);
      } else {
        await baixarReciboPagamento(pagamento.id);
      }
    } catch (err) {
      modal.error('Erro no Recibo', 'Não foi possível gerar o recibo deste pagamento.');
    } finally {
      setProcessando(null);
    }
  };

  // Sem WhatsApp conectado o PDF não sai; o recibo em texto pelo WhatsApp Web ainda funciona.
  const oferecerEnvioEmTexto = (pagamento) => {
    const telefone = (clienteTelefone || pagamento.cliente_telefone || '').replace(/\D/g, '');
    if (!telefone) {
      modal.info(
        'WhatsApp não conectado',
        'Conecte o WhatsApp em Configurações › WhatsApp para enviar o PDF. O cliente também não tem telefone cadastrado para envio manual.',
      );
      return;
    }
    const numero = telefone.startsWith('55') ? telefone : `55${telefone}`;
    const texto = textoReciboWhatsapp(pagamento, clienteNome, emprestimo);
    modal.confirm(
      'WhatsApp não conectado',
      'O PDF não pôde ser enviado porque o WhatsApp não está conectado. Deseja enviar o recibo em texto pelo WhatsApp Web?',
      () => window.open(`https://wa.me/${numero}?text=${encodeURIComponent(texto)}`, '_blank', 'noopener,noreferrer'),
    );
  };

  const enviarWhatsapp = (pagamento) => {
    modal.confirm(
      'Enviar recibo por WhatsApp',
      `Enviar o recibo (PDF) do pagamento de ${formatarMoeda(pagamento.valor_pago || 0)} para o WhatsApp de ${clienteNome}?`,
      async () => {
        setProcessando(pagamento.id);
        try {
          const { data } = ehAmortizacao(pagamento)
            ? await emprestimosAPI.enviarReciboWhatsapp(emprestimo.id, pagamento.id)
            : await pagamentosAPI.enviarReciboWhatsapp(pagamento.id);
          modal.success('Recibo enviado!', data?.message || 'Recibo enviado pelo WhatsApp.');
        } catch (err) {
          if (err.response?.status === 409) {
            oferecerEnvioEmTexto(pagamento);
          } else {
            modal.error('Erro no Envio', err.response?.data?.detail || 'Não foi possível enviar o recibo pelo WhatsApp.');
          }
        } finally {
          setProcessando(null);
        }
      },
    );
  };

  if (erro) {
    return <p className="text-sm text-red-600" data-testid={`historico-erro-${variante}-${emprestimo.id}`}>{erro}</p>;
  }
  if (pagamentos === null) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" /> Carregando pagamentos…
      </div>
    );
  }
  if (pagamentos.length === 0) {
    return <p className="text-sm text-muted-foreground">Nenhum pagamento recebido ainda.</p>;
  }

  return (
    <ul className="divide-y divide-border" data-testid={`historico-pagamentos-${variante}-${emprestimo.id}`}>
      {pagamentos.map((p) => {
        const parcial = p.status_parcela_apos === 'parcial';
        const ocupado = processando === p.id;
        return (
          <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2" data-testid={`pagamento-item-${variante}-${p.id}`}>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-semibold text-foreground">{formatarMoeda(p.valor_pago || 0)}</span>
                <span className="text-muted-foreground">{formatarData(p.data_pagamento)}</span>
                {parcial && (
                  <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 text-xs font-medium">Parcial</span>
                )}
                {ehAmortizacao(p) && (
                  <span className="px-1.5 py-0.5 rounded bg-sky-500/15 text-sky-600 text-xs font-medium">Amortização</span>
                )}
              </div>
              <div className="text-xs text-muted-foreground">
                {ehAmortizacao(p)
                  ? 'Abatimento de capital'
                  : `${emprestimo.sem_prazo ? 'Juros · ' : ''}Parcela ${p.numero_parcela ?? '—'}${p.total_parcelas ? `/${p.total_parcelas}` : ''}`}
                {parcial && p.saldo_parcela_restante != null && ` · ficou faltando ${formatarMoeda(p.saldo_parcela_restante)} nesta parcela`}
                {p.saldo_emprestimo_restante != null && ` · saldo do empréstimo depois: ${formatarMoeda(p.saldo_emprestimo_restante)}`}
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => baixarRecibo(p)}
                disabled={ocupado}
                title="Baixar recibo em PDF"
                className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md border border-border hover:bg-muted disabled:opacity-50"
                data-testid={`btn-recibo-pdf-${variante}-${p.id}`}
              >
                {ocupado ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />} PDF
              </button>
              <button
                type="button"
                onClick={() => enviarWhatsapp(p)}
                disabled={ocupado}
                title="Enviar recibo pelo WhatsApp"
                className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md border border-border hover:bg-muted disabled:opacity-50"
                data-testid={`btn-recibo-whatsapp-${variante}-${p.id}`}
              >
                <MessageCircle className="w-3.5 h-3.5" /> WhatsApp
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
};

export default PagamentosDoEmprestimo;
