import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { cadastroPublicoAPI } from '../api/api';
import { formatarCep } from '../utils/formatters';
import { mascaraCpfCnpj, mascaraTelefone, validarCpfCnpj, validarEmail, validarTelefone } from '../utils/validators';
import { CheckCircle2, Loader2, ShieldCheck, AlertTriangle } from 'lucide-react';

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
    rua: '', numero: '', bairro: '', cidade: '', estado: '', cep: '', observacoes: '',
  });

  useEffect(() => {
    (async () => {
      try {
        const { data } = await cadastroPublicoAPI.info(token);
        setEmpresa(data.empresa);
      } catch {
        setLinkInvalido(true);
      } finally {
        setCarregando(false);
      }
    })();
  }, [token]);

  const set = (campo, valor) => {
    setForm(prev => ({ ...prev, [campo]: valor }));
    if (erros[campo]) setErros(prev => ({ ...prev, [campo]: '' }));
  };

  // Valida um campo individual; retorna mensagem de erro ('' se ok)
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
    setErros(novos);
    return Object.keys(novos).length === 0;
  };

  const handleBlur = (campo) => {
    const msg = validarCampo(campo, form[campo]);
    setErros(prev => ({ ...prev, [campo]: msg }));
  };

  // Máscara de CPF/CNPJ com limite (cap em 14 dígitos)
  const handleCpfChange = (valor) => {
    const dig = valor.replace(/\D/g, '').slice(0, 14);
    set('cpf_cnpj', mascaraCpfCnpj(dig));
  };

  // Máscara de telefone com limite (cap em 11 dígitos)
  const handleTelefoneChange = (valor) => {
    const dig = valor.replace(/\D/g, '').slice(0, 11);
    set('telefone', mascaraTelefone(dig));
  };

  const buscarCep = async (cepValor) => {
    const cep = (cepValor || '').replace(/\D/g, '');
    if (cep.length !== 8) return;
    setBuscandoCep(true);
    try {
      const resp = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const data = await resp.json();
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
      // silencioso: CEP indisponível não bloqueia o cadastro
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
    setEnviando(true);
    try {
      await cadastroPublicoAPI.solicitar(token, {
        nome: form.nome,
        cpf_cnpj: form.cpf_cnpj || null,
        telefone: form.telefone.replace(/\D/g, ''),
        email: form.email || null,
        endereco: {
          rua: form.rua, numero: form.numero, bairro: form.bairro,
          cidade: form.cidade, estado: form.estado, cep: form.cep.replace(/\D/g, ''),
        },
        observacoes: form.observacoes || null,
      });
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
          <h1 className="text-2xl font-bold text-foreground mb-2">Cadastro enviado! 🎉</h1>
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
        {/* Header */}
        <div className="text-center mb-6">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-emerald-600 flex items-center justify-center mx-auto mb-3">
            <span className="text-xl font-bold text-white">K</span>
          </div>
          <h1 className="text-2xl font-bold text-foreground" data-testid="cadastro-empresa">{empresa}</h1>
          <p className="text-muted-foreground text-sm mt-1">Preencha seus dados para solicitar cadastro</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-card border border-border rounded-2xl p-5 sm:p-6 space-y-4" data-testid="form-cadastro-publico">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Nome completo *</label>
            <input className={cls('nome')} value={form.nome} onChange={e => set('nome', e.target.value)} onBlur={() => handleBlur('nome')} placeholder="Seu nome completo" data-testid="input-nome" required />
            {msg('nome')}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">CPF / CNPJ</label>
              <input className={cls('cpf_cnpj')} value={form.cpf_cnpj} onChange={e => handleCpfChange(e.target.value)} onBlur={() => handleBlur('cpf_cnpj')} placeholder="000.000.000-00" data-testid="input-cpf" inputMode="numeric" />
              {msg('cpf_cnpj')}
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">Telefone (WhatsApp) *</label>
              <input className={cls('telefone')} value={form.telefone} onChange={e => handleTelefoneChange(e.target.value)} onBlur={() => handleBlur('telefone')} placeholder="(11) 99999-9999" data-testid="input-telefone" inputMode="numeric" required />
              {msg('telefone')}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">E-mail</label>
            <input className={cls('email')} type="email" value={form.email} onChange={e => set('email', e.target.value)} onBlur={() => handleBlur('email')} placeholder="voce@email.com" data-testid="input-email" />
            {msg('email')}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="relative">
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">CEP</label>
              <input className={cls('cep')} value={form.cep} onChange={e => handleCepChange(e.target.value)} onBlur={e => buscarCep(e.target.value)} placeholder="00000-000" data-testid="input-cep" inputMode="numeric" />
              {buscandoCep && <Loader2 className="w-4 h-4 text-primary animate-spin absolute right-3 top-[34px]" data-testid="cep-loading" />}
              {msg('cep')}
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">Rua</label>
              <input className={inputCls} value={form.rua} onChange={e => set('rua', e.target.value)} placeholder="Rua / Avenida" data-testid="input-rua" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">Número</label>
              <input className={inputCls} value={form.numero} onChange={e => set('numero', e.target.value)} placeholder="Nº" data-testid="input-numero" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">Bairro</label>
              <input className={inputCls} value={form.bairro} onChange={e => set('bairro', e.target.value)} placeholder="Bairro" data-testid="input-bairro" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">Cidade</label>
              <input className={inputCls} value={form.cidade} onChange={e => set('cidade', e.target.value)} placeholder="Cidade" data-testid="input-cidade" />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">UF</label>
              <input className={inputCls} value={form.estado} onChange={e => set('estado', e.target.value.toUpperCase().slice(0, 2))} placeholder="SP" data-testid="input-estado" maxLength={2} />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Observações</label>
            <textarea className={inputCls} rows={3} value={form.observacoes} onChange={e => set('observacoes', e.target.value)} placeholder="Alguma informação adicional..." data-testid="input-observacoes" />
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
