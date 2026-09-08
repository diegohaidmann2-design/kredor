import React from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';
import { Button } from '../../components/ui/button';

const formatarPreco = (v) =>
  `R$ ${Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const formatarLimite = (v) => (v === -1 || v == null ? 'Ilimitados' : v);

const PlanCard = ({ nome, preco, popular, clientes, emprestimos, extras, isDark }) => (
  <div
    className={`rounded-2xl border p-6 flex flex-col ${
      popular ? 'border-primary bg-primary/10' : isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-slate-200'
    }`}
    data-testid={`plano-${nome.toLowerCase()}`}
  >
    {popular && (
      <span className="self-start mb-3 text-xs font-semibold bg-primary text-white rounded-full px-3 py-1">Mais popular</span>
    )}
    <h3 className="text-lg font-display font-semibold">{nome}</h3>
    <div className="mt-2 mb-4">
      <span className="text-3xl font-display font-bold">{formatarPreco(preco)}</span>
      <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>/mês</span>
    </div>
    <ul className="space-y-2 mb-6 text-sm flex-1">
      <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-primary" /> Até {formatarLimite(clientes)} clientes</li>
      <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-primary" /> Até {formatarLimite(emprestimos)} empréstimos</li>
      {extras.map((e, i) => (
        <li key={i} className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-primary" /> {e}</li>
      ))}
    </ul>
    <Link to="/login">
      <Button className={`w-full ${popular ? 'bg-primary hover:bg-primary/90 text-white' : ''}`} variant={popular ? 'default' : 'outline'}>
        Começar teste grátis
      </Button>
    </Link>
  </div>
);

const Precos = () => (
  <CommercialLanding
    seo={{
      title: 'Preços e planos do GestorCred | Gestão de empréstimos',
      description: 'Conheça os planos do GestorCred para gestão de empréstimos e cobrança. Comece com 7 dias grátis, sem cartão de crédito. Cancele quando quiser.',
      path: '/precos',
    }}
    eyebrow="Planos e preços"
    h1="Planos do GestorCred para cada tamanho de carteira"
    subtitle="Escolha o plano ideal para o seu volume de clientes e empréstimos. Todos incluem cobrança PIX, régua no WhatsApp e controle de parcelas. Comece com 7 dias grátis."
    heroBullets={[
      'Sem cartão de crédito para testar',
      'Cancele quando quiser',
      'Todos os planos com PIX e WhatsApp',
      'Suporte para começar rápido',
    ]}
    faq={[
      { q: 'Como funciona o teste grátis?', a: 'Você cria sua conta e usa o sistema por 7 dias sem cobrança e sem cartão de crédito. Ao final, escolhe o plano que preferir.' },
      { q: 'Posso trocar de plano depois?', a: 'Sim. Você pode subir ou descer de plano conforme o crescimento da sua carteira.' },
      { q: 'Preciso pagar por maquininha ou taxa extra de PIX?', a: 'Não há maquininha. O recebimento é por PIX, integrado ao sistema com baixa automática.' },
    ]}
    related={[
      { to: '/sistema-gestao-emprestimos', label: 'Sistema de gestão de empréstimos' },
      { to: '/cobranca-pix', label: 'Cobrança por PIX' },
      { to: '/cobranca-whatsapp', label: 'Cobrança no WhatsApp' },
      { to: '/como-funciona', label: 'Como funciona' },
    ]}
    ctaTitle="Comece grátis hoje"
    ctaText="7 dias grátis, sem cartão de crédito. Depois, escolha o plano ideal."
  >
    {({ config, isDark }) => (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6" data-testid="precos-grid">
        <PlanCard
          nome="Básico"
          preco={config.plano_basico_preco ?? 97}
          clientes={config.plano_basico_clientes ?? 50}
          emprestimos={config.plano_basico_emprestimos ?? 100}
          extras={['Cobrança PIX e WhatsApp', 'Relatórios básicos', 'Suporte por e-mail']}
          isDark={isDark}
        />
        <PlanCard
          nome="Profissional"
          preco={config.plano_profissional_preco ?? 197}
          clientes={config.plano_profissional_clientes ?? 200}
          emprestimos={config.plano_profissional_emprestimos ?? 500}
          extras={['Régua de cobrança automática', 'Contratos digitais (CCB)', 'Relatórios avançados', 'Portal do cliente']}
          popular
          isDark={isDark}
        />
        <PlanCard
          nome="Empresarial"
          preco={config.plano_enterprise_preco ?? 497}
          clientes={config.plano_enterprise_clientes ?? -1}
          emprestimos={config.plano_enterprise_emprestimos ?? -1}
          extras={['Recursos ilimitados', 'Score e análise de risco', 'Assistente com IA', 'Suporte prioritário']}
          isDark={isDark}
        />
      </div>
    )}
  </CommercialLanding>
);

export default Precos;
