import React, { useEffect, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { pagamentosAPI } from '../../api/api';
import { formatarMoeda } from '../../utils/formatters';

/**
 * Avisa que o valor informado não quita a parcela e pergunta se o restante deve ser ignorado.
 *
 * Multa e mora dependem da data em que o cliente pagou, então quem sabe quanto a parcela devia
 * naquele dia é o servidor: o componente consulta a prévia a cada mudança de valor ou data.
 * Sem marcar a opção nada muda — a parcela fica parcial, como sempre foi.
 */
const RestanteDoPagamento = ({ parcelaId, valorPago, dataPagamento, ignorar, onChangeIgnorar }) => {
  const [previa, setPrevia] = useState(null);

  const valor = parseFloat(valorPago);

  useEffect(() => {
    if (!parcelaId || !(valor > 0)) {
      setPrevia(null);
      return undefined;
    }

    let cancelado = false;
    // Espera a digitação parar para não consultar a cada tecla no valor.
    const timer = setTimeout(async () => {
      try {
        const { data } = await pagamentosAPI.previa({
          parcela_id: parcelaId,
          valor_pago: valor,
          data_pagamento: dataPagamento || undefined,
        });
        if (!cancelado) setPrevia(data);
      } catch (err) {
        // Sem a prévia o lançamento continua funcionando: a parcela só fica parcial.
        if (!cancelado) setPrevia(null);
      }
    }, 400);

    return () => { cancelado = true; clearTimeout(timer); };
  }, [parcelaId, valor, dataPagamento]);

  // Enquanto o valor quita a parcela não há nada a perguntar, e a opção não pode ficar marcada.
  useEffect(() => {
    if ((!previa || previa.quita) && ignorar) onChangeIgnorar(false);
  }, [previa, ignorar, onChangeIgnorar]);

  if (!previa || previa.quita || !(previa.restante > 0)) return null;

  const detalhe = previa.restante_detalhe || {};
  const partes = [
    [detalhe.encargos, 'de multa e mora'],
    [detalhe.juros, 'de juros'],
    [detalhe.capital, 'de capital'],
  ].filter(([v]) => v > 0).map(([v, rotulo]) => `${formatarMoeda(v)} ${rotulo}`);

  return (
    <div
      className="rounded-md border border-amber-500/50 bg-amber-500/10 p-3 space-y-2"
      data-testid="restante-do-pagamento"
    >
      <div className="flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
        <div className="text-sm text-foreground">
          <p>
            Esse valor não quita a parcela: nesta data ela deve{' '}
            <strong>{formatarMoeda(previa.devido)}</strong> e faltam{' '}
            <strong>{formatarMoeda(previa.restante)}</strong>
            {previa.dias_atraso > 0 && ` (${previa.dias_atraso} dia(s) de atraso)`}.
          </p>
          {partes.length > 0 && (
            <p className="text-xs text-muted-foreground mt-1">Restante: {partes.join(' + ')}.</p>
          )}
        </div>
      </div>

      <label className="flex items-start gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={!!ignorar}
          onChange={(e) => onChangeIgnorar(e.target.checked)}
          className="mt-0.5 h-4 w-4 rounded border-border accent-amber-500"
          data-testid="checkbox-ignorar-restante"
        />
        <span className="text-sm text-foreground">
          Dar a parcela por <strong>quitada</strong> e não cobrar os {formatarMoeda(previa.restante)}.
          <span className="block text-xs text-muted-foreground">
            O valor perdoado não entra como recebido e sai do total a receber.
          </span>
        </span>
      </label>
    </div>
  );
};

export default RestanteDoPagamento;
