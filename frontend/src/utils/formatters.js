// Importar funções de timezone
import { formatDateBR, formatDateTimeFull } from './timezone';

// Formatar valor monetário
export const formatarMoeda = (valor) => {
  try {
    const numero = parseFloat(valor) || 0;
    return numero.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  } catch (error) {
    console.error('Erro ao formatar moeda:', error);
    return `R$ ${(parseFloat(valor) || 0).toFixed(2)}`;
  }
};

// Formatar data
export const formatarData = (data) => {
  if (!data) return '-';
  try {
    // Usar timezone de São Paulo
    return formatDateBR(data, false);
  } catch (error) {
    console.error('Erro ao formatar data:', error);
    return '-';
  }
};

// Formatar data e hora
export const formatarDataHora = (data) => {
  if (!data) return '-';
  try {
    // Usar timezone de São Paulo
    return formatDateBR(data, true);
  } catch (error) {
    console.error('Erro ao formatar data e hora:', error);
    return '-';
  }
};

// Formatar CPF/CNPJ
export const formatarCpfCnpj = (valor) => {
  if (!valor) return '';

  const numeros = valor.replace(/\D/g, '');

  if (numeros.length === 11) {
    return numeros.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
  } else if (numeros.length === 14) {
    return numeros.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
  }

  return valor;
};

// Formatar telefone
export const formatarTelefone = (valor) => {
  if (!valor) return '';

  const numeros = valor.replace(/\D/g, '');

  if (numeros.length === 11) {
    return numeros.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
  } else if (numeros.length === 10) {
    return numeros.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
  }

  return valor;
};

// Formatar CEP
export const formatarCep = (valor) => {
  if (!valor) return '';
  const numeros = valor.replace(/\D/g, '');
  return numeros.replace(/(\d{5})(\d{3})/, '$1-$2');
};

// Calcular dias entre datas
export const calcularDias = (dataInicio, dataFim) => {
  const inicio = new Date(dataInicio);
  const fim = new Date(dataFim);
  const diff = Math.abs(fim - inicio);
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
};

// Obter cor do status (tema dark)
export const getStatusColor = (status) => {
  const colors = {
    ativo: 'text-primary bg-primary/10 border-primary/20',
    pendente: 'text-warning bg-warning/10 border-warning/20',
    pago: 'text-primary bg-primary/10 border-primary/20',
    atrasado: 'text-destructive bg-destructive/10 border-destructive/20',
    inadimplente: 'text-destructive bg-destructive/10 border-destructive/20',
    quitado: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
    bloqueado: 'text-muted-foreground bg-muted border-muted',
    renegociado: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
    parcial: 'text-orange-400 bg-orange-400/10 border-orange-400/20'
  };

  return colors[status] || 'text-muted-foreground bg-muted border-muted';
};

// Obter label do status
export const getStatusLabel = (status) => {
  const labels = {
    ativo: 'Ativo',
    pendente: 'Pendente',
    pago: 'Pago',
    atrasado: 'Atrasado',
    inadimplente: 'Inadimplente',
    quitado: 'Quitado',
    bloqueado: 'Bloqueado',
    renegociado: 'Renegociado',
    parcial: 'Parcial'
  };

  return labels[status] || status;
};

// Obter label do método de cálculo
export const getMetodoCalculoLabel = (metodo) => {
  const labels = {
    juros_simples: 'Juros Simples',
    juros_compostos: 'Juros Compostos',
    tabela_price: 'Tabela Price',
    sac: 'SAC',
    apenas_juros: 'Apenas Juros',
    // Aliases antigos (caso existam no BD)
    simples: 'Juros Simples',
    composto: 'Juros Compostos',
    price: 'Tabela Price'
  };

  return labels[metodo] || metodo;
};

// Formatar erro da API (previne erros de renderização com objetos)
export const formatarErroAPI = (error, defaultMessage = 'Ocorreu um erro. Tente novamente.') => {
  // Se não tem response (erro de rede, etc)
  if (!error?.response) return error?.message || defaultMessage;

  const data = error.response.data;
  if (!data) return defaultMessage;

  // Se detail é uma string simples
  if (typeof data.detail === 'string') {
    return data.detail;
  }

  // Se detail é um array (Pydantic Validation Error)
  if (Array.isArray(data.detail)) {
    try {
      // Mapeamento de campos para nomes amigáveis
      const fieldNames = {
        'cpf_cnpj': 'CPF/CNPJ',
        'nome': 'Nome',
        'email': 'E-mail',
        'telefone': 'Telefone',
        'endereco': 'Endereço',
        'rua': 'Rua',
        'numero': 'Número',
        'bairro': 'Bairro',
        'cidade': 'Cidade',
        'estado': 'Estado',
        'cep': 'CEP'
      };

      return data.detail.map(err => {
        // Pega o campo
        const fieldKey = err.loc && err.loc.length > 0
          ? err.loc[err.loc.length - 1]
          : 'Campo';
        
        const field = fieldNames[fieldKey] || fieldKey;

        // Traduz mensagens comuns
        let msg = err.msg;
        if (msg === 'field required') msg = 'é obrigatório';
        if (msg === 'Field required') msg = 'é obrigatório';
        if (msg.includes('CPF/CNPJ inválido')) msg = 'inválido. Verifique os dígitos';
        if (msg.includes('Input should be a valid dictionary')) msg = 'formato inválido';
        if (msg.includes('Value error')) msg = msg.replace('Value error, ', '');

        return `${field}: ${msg}`;
      }).join('\n');
    } catch (e) {
      return 'Erro de validação. Verifique os campos e tente novamente.';
    }
  }

  // Fallback para detail sendo objeto ou outro tipo
  if (typeof data.detail === 'object') {
    return JSON.stringify(data.detail);
  }

  return defaultMessage;
};

/** Hoje no formato que a API espera (AAAA-MM-DD), pelo calendário local. */
export const hojeISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
