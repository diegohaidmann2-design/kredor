import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { cadastroPublicoAPI, cepAPI } from '../api/api';
import { formatarCep } from '../utils/formatters';
import { mascaraCpfCnpj, mascaraTelefone, validarCpfCnpj, validarEmail, validarTelefone } from '../utils/validators';
import { dataUrlToBlob } from '../utils/imageCompress';
import CameraCapture from '../components/cadastro-publico/CameraCapture';
import SignaturePad from '../components/cadastro-publico/SignaturePad';
import { CheckCircle2, Loader2, ShieldCheck, AlertTriangle } from 'lucide-react';

function useBlobPreview(blob) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    if (!blob) { setUrl(null); return; }
    const u = URL.createObjectURL(blob);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [blob]);
  return url;
}

const CadastroPublico = () => {
  const { token } = useParams();
  const [carregando, setCarregando] = useState(true);
  const [empresa, setEmpresa] = useState('');
  const [linkInvalido, setLinkInvalido] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [erro, setErro] = useState('');
  const [buscandoCep, setBuscandoCep] = useState(false);
  const [erros, setErros] = useState({});
  const [form, setForm] = useState({
    nome: '', cpf_cnpj: '', telefone: '', email: '',
    rua: '', numero: '', complemento: '', bairro: '', cidade: '', estado: '', cep: '', observacoes: '',
    renda_mensal: '', tipo_emprego: '', valor_emprestimo: '',
  });

  // Anexos
  const [selfieBlob, setSelfieBlob] = useState(null);
  const [docFrenteBlob, setDocFrenteBlob] = useState(null);
  const [docVersoBlob, setDocVersoBlob] = useState(null);
  const [assinaturaDataUrl, setAssinaturaDataUrl] = useState(null);
  const [consentimento, setConsentimento] = useState(false);
  const [rascunhoRecuperado, setRascunhoRecuperado] = useState(false);

  const selfiePreview = useBlobPreview(selfieBlob);
  const docFrentePreview = useBlobPreview(docFrenteBlob);
  const docVersoPreview = useBlobPreview(docVersoBlob);

  const temAnexo = !!(selfieBlob || docFrenteBlob || docVersoBlob || assinaturaDataUrl);

  useEffect(() => {
    if (!token) {
      setLinkInvalido(true);
      setCarregando(false);
      return;
    }
    (async () => {
      try {
        const { data } = await cadastroPublicoAPI.info(token);
        setEmpresa(data.empresa);

        // Restaurar rascunho salvo do localStorage se existir
        try {
          const salvo = localStorage.getItem(`kredor_draft_${token}`);
          if (salvo) {
            const d = JSON.parse(salvo);
            if (d.form) setForm(prev => ({ ...prev, ...d.form }));
            if (d.assinaturaDataUrl) setAssinaturaDataUrl(d.assinaturaDataUrl);
            if (typeof d.consentimento === 'boolean') setConsentimento(d.consentimento);
            setRascunhoRecuperado(true);
          }
        } catch {
          // silencioso
        }
      } catch {
        setLinkInvalido(true);
      } finally {
        setCarregando(false);
      }
    })();
  }, [token]);

  // Salvar rascunho automaticamente a cada alteração
  useEffect(() => {
    if (!token || carregando || linkInvalido || enviado) return;
    try {
      const temDados = Object.values(form).some(v => !!v) || !!assinaturaDataUrl || consentimento;
      if (temDados) {
        localStorage.setItem(`kredor_draft_${token}`, JSON.stringify({
          form,
          assinaturaDataUrl,
          consentimento,
          updatedAt: Date.now(),
        }));
      }
    } catch {
      // quota/storage restrito
    }
  }, [form, assinaturaDataUrl, consentimento, token, carregando, linkInvalido, enviado]);

  const set = (campo, valor) => {
    setForm(prev => ({ ...prev, [campo]: valor }));
    if (erros[campo]) setErros(prev => ({ ...prev, [campo]: '' }));
  };

  const validarCampo = (campo, valor) => {
    switch (campo) {
      case 'nome':
        return valor.trim().length < 3 ? 'Informe o nome completo (mín. 3 letras).' : '';
      case 'cpf_cnpj': {
        const dig = valor.replace(/\D/g, '');
        if (!dig) return '';
        if (dig.length !== 11 && dig.length !== 14) return 'CPF deve ter 11 e CNPJ 14 dígitos.';
        return validarCpfCnpj(valor) ? '' : 'CPF/CNPJ inválido. Confira os números.';
      }
      case 'telefone':
        return validarTelefone(valor) ? '' : 'Telefone inválido. Use DDD + número.';
      case 'email':
        return !valor ? '' : (validarEmail(valor) ? '' : 'E-mail inválido.');
      default:
        return '';
    }
  };

  const validarTudo = () => {
    const novos = {};
    ['nome', 'cpf_cnpj', 'telefone', 'email'].forEach(c => {
      const msg = validarCampo(c, form[c]);
      if (msg) novos[c] = msg;
    });
    // Se há anexos, consentimento é obrigatório
    if (temAnexo && !consentimento) {
      novos.consentimento = 'Você precisa autorizar o uso das imagens.';
    }
    setErros(novos);
    return Object.keys(novos).length === 0;
  };

  const handleBlur = (campo) => {
    const msg = validarCampo(campo, form[campo]);
    setErros(prev => ({ ...prev, [campo]: msg }));
  };

  const handleCpfChange = (valor) => {
    const dig = valor.replace(/\D/g, '').slice(0, 14);
    set('cpf_cnpj', mascaraCpfCnpj(dig));
  };

  const handleTelefoneChange = (valor) => {
    const dig = valor.replace(/\D/g, '').slice(0, 11);
    set('telefone', mascaraTelefone(dig));
  };

  const buscarCep = async (cepValor) => {
    const cep = (cepValor || '').replace(/\D/g, '');
    if (cep.length !== 8) return;
    setBuscandoCep(true);
    try {
      const data = await cepAPI.consultar(cep);
      if (!data.erro) {
        setForm(prev => ({
          ...prev,
          rua: data.logradouro || prev.rua,
          bairro: data.bairro || prev.bairro,
          cidade: data.localidade || prev.cidade,
          estado: data.uf || prev.estado,
        }));
        setErros(prev => ({ ...prev, cep: '' }));
      } else {
        setErros(prev => ({ ...prev, cep: 'CEP não encontrado.' }));
      }
    } catch {
      // silencioso
    } finally {
      setBuscandoCep(false);
    }
  };

  const handleCepChange = (valor) => {
    const formatado = formatarCep(valor);
    set('cep', formatado);
    if (formatado.replace(/\D/g, '').length === 8) buscarCep(formatado);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErro('');
    if (!validarTudo()) {
      setErro('Corrija os campos destacados antes de enviar.');
      return;
    }
    if (temAnexo && !consentimento) {
      setErro('Autorize o uso das imagens e documentos para continuar.');
      return;
    }
    setEnviando(true);
    try {
      const temArquivos = !!(selfieBlob || docFrenteBlob || docVersoBlob || assinaturaDataUrl);
      if (temArquivos) {
        const fd = new FormData();
        fd.append('nome', form.nome);
        fd.append('cpf_cnpj', form.cpf_cnpj || '');
        fd.append('telefone', form.telefone.replace(/\D/g, ''));
        fd.append('email', form.email || '');
        fd.append('rua', form.rua || '');
        fd.append('numero', form.numero || '');
        fd.append('complemento', form.complemento || '');
        fd.append('bairro', form.bairro || '');
        fd.append('cidade', form.cidade || '');
        fd.append('estado', form.estado || '');
        fd.append('cep', form.cep.replace(/\D/g, '') || '');
        fd.append('observacoes', form.observacoes || '');
        fd.append('renda_mensal', form.renda_mensal || '');
        fd.append('tipo_emprego', form.tipo_emprego || '');
        fd.append('valor_emprestimo', form.valor_emprestimo || '');
        fd.append('consentimento', consentimento ? 'true' : 'false');
        fd.append('versao_termo', 'v1-2026-09');
        if (selfieBlob) fd.append('selfie', selfieBlob, 'selfie.jpg');
        if (docFrenteBlob) fd.append('doc_frente', docFrenteBlob, 'doc_frente.jpg');
        if (docVersoBlob) fd.append('doc_verso', docVersoBlob, 'doc_verso.jpg');
        if (assinaturaDataUrl) {
          const blob = dataUrlToBlob(assinaturaDataUrl);
          fd.append('assinatura', blob, 'assinatura.png');
        }
        await cadastroPublicoAPI.solicitarMultipart(token, fd);
      } else {
        await cadastroPublicoAPI.solicitar(token, {
          nome: form.nome,
          cpf_cnpj: form.cpf_cnpj || null,
          telefone: form.telefone.replace(/\D/g, ''),
          email: form.email || null,
          endereco: {
            rua: form.rua, numero: form.numero, complemento: form.complemento || '', bairro: form.bairro,
            cidade: form.cidade, estado: form.estado, cep: form.cep.replace(/\D/g, ''),
          },
          observacoes: form.observacoes || null,
          renda_mensal: form.renda_mensal || null,
          tipo_emprego: form.tipo_emprego || null,
          valor_emprestimo: form.valor_emprestimo || null,
        });
      }
      // Limpeza do rascunho salvo no localStorage após envio bem-sucedido
      try {
        localStorage.removeItem(`kredor_draft_${token}`);
      } catch {}
      setEnviado(true);
    } catch (err) {
      setErro(err.response?.data?.detail || 'Não foi possível enviar. Verifique os dados e tente novamente.');
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
        <div className="max-w-md text-center" data-testid="link-invalido">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-foreground mb-2">Link inválido ou expirado</h1>
          <p className="text-muted-foreground">Peça um novo link de cadastro ao responsável.</p>
        </div>
      </div>
    );
  }

  if (enviado) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-4">
        <div className="max-w-md text-center" data-testid="cadastro-enviado">
          <CheckCircle2 className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
          <h1 className="font-cabinet font-black text-2xl tracking-tight text-foreground mb-2">Cadastro enviado!</h1>
          <p className="text-muted-foreground">
            Recebemos seus dados. <strong className="text-foreground">{empresa}</strong> vai analisar e entrar em contato em breve.
          </p>
        </div>
      </div>
    );
  }

  const inputCls = "w-full px-3 py-2.5 bg-background border border-border rounded-lg text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary";
  const cls = (campo) => `${inputCls} ${erros[campo] ? '!border-red-500 focus:ring-red-500' : ''}`;
  const msg = (campo) => erros[campo] ? <p className="mt-1 text-xs text-red-500" data-testid={`erro-${campo}`}>{erros[campo]}</p> : null;

  return (
    <div className="min-h-screen bg-background py-8 px-4">
      <div className="max-w-xl mx-auto">
        <div className="text-center mb-6">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-emerald-600 flex items-center justify-center mx-auto mb-3">
            <span className="text-xl font-bold text-white">K</span>
          </div>
          <h1 className="font-cabinet font-black text-2xl tracking-tight text-foreground" data-testid="cadastro-empresa">{empresa}</h1>
          <p className="text-muted-foreground text-sm mt-1">Preencha seus dados para solicitar cadastro</p>
        </div>

        {rascunhoRecuperado && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-xs flex items-center justify-between" data-testid="rascunho-banner">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Restauramos suas informações salvas anteriormente neste dispositivo.
            </span>
            <button
              type="button"
              onClick={() => setRascunhoRecuperado(false)}
              className="text-muted-foreground hover:text-foreground font-bold p-1"
              title="Fechar aviso"
            >
              &times;
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-card border border-border rounded-2xl p-5 sm:p-6 space-y-4" data-testid="form-cadastro-publico">
          <div>
            <label className="block text-xs font-medium text-foreground mb-1.5">Nome completo *</label>
            <input className={cls('nome')} value={form.nome} onChange={e => set('nome', e.target.value)} onBlur={() => handleBlur('nome')} placeholder="Seu nome completo" data-testid="input-nome" required />
            {msg('nome')}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-foreground mb-1.5">CPF / CNPJ</label>
              <input className={cls('cpf_cnpj')} value={form.cpf_cnpj} onChange={e => handleCpfChange(e.target.value)} onBlur={() => handleBlur('cpf_cnpj')} placeholder="000.000.000-00" data-testid="input-cpf" inputMode="numeric" />
              {msg('cpf_cnpj')}
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1.5">Telefone (WhatsApp) *</label>
              <input className={cls('telefone')} value={form.telefone} onChange={e => handleTelefoneChange(e.target.value)} onBlur={() => handleBlur('telefone')} placeholder="(11) 99999-9999" data-testid="input-telefone" inputMode="numeric" required />
              {msg('telefone')}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-foreground mb-1.5">E-mail</label>
            <input className={cls('email')} type="email" value={form.email} onChange={e => set('email', e.target.value)} onBlur={() => handleBlur('email')} placeholder="voce@email.com" data-testid="input-email" />
            {msg('email')}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="relative">
              <label className="block text-xs font-medium text-foreground mb-1.5">CEP</label>
              <input className={cls('cep')} value={form.cep} onChange={e => handleCepChange(e.target.value)} onBlur={e => buscarCep(e.target.value)} placeholder="00000-000" data-testid="input-cep" inputMode="numeric" />
              {buscandoCep && <Loader2 className="w-4 h-4 text-primary animate-spin absolute right-3 top-[34px]" data-testid="cep-loading" />}
              {msg('cep')}
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-foreground mb-1.5">Rua</label>
              <input className={inputCls} value={form.rua} onChange={e => set('rua', e.target.value)} placeholder="Rua / Avenida" data-testid="input-rua" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-foreground mb-1.5">Número</label>
              <input className={inputCls} value={form.numero} onChange={e => set('numero', e.target.value)} placeholder="Nº" data-testid="input-numero" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-foreground mb-1.5">Bairro</label>
              <input className={inputCls} value={form.bairro} onChange={e => set('bairro', e.target.value)} placeholder="Bairro" data-testid="input-bairro" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-foreground mb-1.5">Complemento</label>
            <input className={inputCls} value={form.complemento} onChange={e => set('complemento', e.target.value)} placeholder="Apto, bloco, referência (opcional)" data-testid="input-complemento" />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-foreground mb-1.5">Cidade</label>
              <input className={inputCls} value={form.cidade} onChange={e => set('cidade', e.target.value)} placeholder="Cidade" data-testid="input-cidade" />
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1.5">UF</label>
              <input className={inputCls} value={form.estado} onChange={e => set('estado', e.target.value.toUpperCase().slice(0, 2))} placeholder="SP" data-testid="input-estado" maxLength={2} />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-foreground mb-1.5">Observações</label>
            <textarea className={inputCls} rows={3} value={form.observacoes} onChange={e => set('observacoes', e.target.value)} placeholder="Alguma informação adicional..." data-testid="input-observacoes" />
          </div>

          {/* Informações Financeiras */}
          <div className="pt-2 border-t border-border space-y-3">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Informações financeiras</h3>
              <p className="text-xs text-muted-foreground">Ajuda na análise do seu pedido. Todos os campos são opcionais.</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-foreground mb-1.5">Situação de emprego</label>
              <select
                className={inputCls}
                value={form.tipo_emprego}
                onChange={e => set('tipo_emprego', e.target.value)}
                data-testid="input-tipo-emprego"
              >
                <option value="">Selecione...</option>
                <option value="Carteira Assinada (CLT)">Carteira Assinada (CLT)</option>
                <option value="Autônomo">Autônomo</option>
                <option value="MEI">MEI (Microempreendedor Individual)</option>
                <option value="Empresário">Empresário / Sócio</option>
                <option value="Aposentado / Pensionista">Aposentado / Pensionista</option>
                <option value="Servidor Público">Servidor Público</option>
                <option value="Outro">Outro</option>
              </select>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-foreground mb-1.5">Renda mensal (R$)</label>
                <input
                  className={inputCls}
                  type="text"
                  inputMode="decimal"
                  value={form.renda_mensal}
                  onChange={e => {
                    const v = e.target.value.replace(/[^0-9,.]/g, '');
                    set('renda_mensal', v);
                  }}
                  placeholder="Ex: 3.500,00"
                  data-testid="input-renda-mensal"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-foreground mb-1.5">Valor do empréstimo desejado (R$)</label>
                <input
                  className={inputCls}
                  type="text"
                  inputMode="decimal"
                  value={form.valor_emprestimo}
                  onChange={e => {
                    const v = e.target.value.replace(/[^0-9,.]/g, '');
                    set('valor_emprestimo', v);
                  }}
                  placeholder="Ex: 10.000,00"
                  data-testid="input-valor-emprestimo"
                />
              </div>
            </div>
          </div>

          {/* Anexos */}
          <div className="pt-2 border-t border-border space-y-3" data-testid="secao-anexos">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Documentos e assinatura</h3>
              <p className="text-xs text-muted-foreground">Envie sua foto, documento e assinatura para agilizar a aprovação. Todos os campos são opcionais.</p>
            </div>

            <CameraCapture
              label="Selfie"
              hint="Foto do rosto, de frente e com boa iluminação"
              facingMode="user"
              value={selfieBlob}
              previewUrl={selfiePreview}
              onChange={setSelfieBlob}
              preset="selfie"
              overlay="oval"
              testId="anexo-selfie"
            />
            <CameraCapture
              label="Documento — frente"
              hint="RG, CNH ou outro documento com foto"
              facingMode="environment"
              value={docFrenteBlob}
              previewUrl={docFrentePreview}
              onChange={setDocFrenteBlob}
              preset="documento"
              overlay="rect"
              testId="anexo-doc-frente"
            />
            <CameraCapture
              label="Documento — verso"
              hint="Verso do mesmo documento"
              facingMode="environment"
              value={docVersoBlob}
              previewUrl={docVersoPreview}
              onChange={setDocVersoBlob}
              preset="documento"
              overlay="rect"
              testId="anexo-doc-verso"
            />
            <SignaturePad
              value={assinaturaDataUrl}
              onChange={setAssinaturaDataUrl}
              testId="anexo-assinatura"
            />

            <label className={`flex items-start gap-2 p-3 rounded-lg border text-sm cursor-pointer ${erros.consentimento ? 'border-red-500 bg-red-500/5' : 'border-border bg-muted/20'}`} data-testid="consentimento-label">
              <input
                type="checkbox"
                checked={consentimento}
                onChange={e => {
                  setConsentimento(e.target.checked);
                  if (erros.consentimento) setErros(prev => ({ ...prev, consentimento: '' }));
                }}
                className="mt-0.5 w-4 h-4 rounded border-border"
                data-testid="input-consentimento"
              />
              <span className="text-xs text-muted-foreground leading-snug">
                Li e autorizo o uso das minhas imagens, documentos e assinatura para análise de cadastro pela <strong className="text-foreground">{empresa}</strong> (termo v1-2026-09). Os arquivos serão usados apenas para validação da ficha.
              </span>
            </label>
            {erros.consentimento && <p className="text-xs text-red-500" data-testid="erro-consentimento">{erros.consentimento}</p>}
            {temAnexo && !consentimento && <p className="text-xs text-amber-600">Autorize o uso para enviar os anexos.</p>}
          </div>

          {erro && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 text-red-500 text-sm" data-testid="cadastro-erro">
              <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" /> {erro}
            </div>
          )}

          <button
            type="submit"
            disabled={enviando}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-primary text-primary-foreground font-semibold hover:opacity-90 transition-opacity disabled:opacity-60"
            data-testid="btn-enviar-cadastro"
          >
            {enviando ? <><Loader2 className="w-4 h-4 animate-spin" /> Enviando...</> : 'Enviar cadastro'}
          </button>

          <p className="flex items-center justify-center gap-1.5 text-xs text-muted-foreground">
            <ShieldCheck className="w-3.5 h-3.5 text-primary" /> Seus dados são enviados com segurança.
          </p>
        </form>
      </div>
    </div>
  );
};

export default CadastroPublico;
