import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle } from 'lucide-react';
import CommercialLanding from '../components/CommercialLanding';
import { Button } from '../components/ui/button';
import { assinaturasAPI } from '../api/api';
import { planosPrerender } from '../lib/prerender';

const formatarPreco = (v) =>
  `R$ ${Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const formatarLimite = (v) => (v === -1 || v == null ? 'Ilimitados' : v);

const PlanCard = ({ nome, preco, popular, clientes, emprestimos, extras, isDark, ciclo }) => (
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
    {/* No ciclo longo o número grande é o valor POR MÊS: é assim que o visitante compara
        planos. O total cobrado vem logo abaixo, sem letra miúda — cobrar R$ 800 de uma vez
        mostrando só "R$ 66,67/mês" seria esconder o que sai do bolso dele hoje. */}
    <div className="mt-2 mb-4">
      <span className="text-3xl font-display font-bold">
        {formatarPreco(ciclo ? ciclo.preco_por_mes : preco)}
      </span>
      <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>/mês</span>
      {ciclo && ciclo.ciclo !== 'mensal' && (
        <div className="mt-1 space-y-0.5">
          <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            {formatarPreco(ciclo.preco_total)} cobrados por {ciclo.meses} meses
          </p>
          <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
            Economize {formatarPreco(ciclo.economia)} ({ciclo.desconto_percentual}% off)
          </p>
        </div>
      )}
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

/**
 * Grade de planos com o seletor de ciclo.
 *
 * Os ciclos vêm de GET /assinaturas/planos, calculados pelo servidor — a mesma fonte que
 * cobra. Se a tela repetisse a conta do desconto, o preço anunciado poderia divergir do
 * cobrado, e numa página de preços isso é oferta enganosa, não bug de layout.
 *
 * O prerender do build roda sem alcançar a API: sem os ciclos, a grade cai no preço mensal
 * da configuração, que é exatamente o que esta página mostrava antes. Nenhuma regressão de
 * SEO, e o seletor aparece depois que a página hidrata.
 */
const GradePlanos = ({ config, isDark }) => {
  // Semente do que o prerender injetou: o HTML estático já sai com o seletor e os preços
  // certos, em vez de esperar a hidratação para corrigir números que o Google já indexou.
  const semente = () => {
    const lista = planosPrerender();
    if (!Array.isArray(lista)) return { ciclos: [], porNivel: {} };
    const porNivel = {};
    lista.forEach((p) => {
      if ((p.ciclos || []).length) {
        porNivel[p.id] = Object.fromEntries(p.ciclos.map((c) => [c.ciclo, c]));
      }
    });
    const ref = lista.find((p) => (p.ciclos || []).length);
    return { ciclos: ref ? ref.ciclos : [], porNivel };
  };

  const [ciclos, setCiclos] = useState(() => semente().ciclos);
  const [ciclo, setCiclo] = useState('mensal');
  const [porNivel, setPorNivel] = useState(() => semente().porNivel);

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const { data } = await assinaturasAPI.listarPlanos();
        if (!ativo || !Array.isArray(data)) return;

        const mapa = {};
        data.forEach((p) => {
          if ((p.ciclos || []).length) {
            mapa[p.id] = Object.fromEntries(p.ciclos.map((c) => [c.ciclo, c]));
          }
        });
        const referencia = data.find((p) => (p.ciclos || []).length);
        if (referencia) setCiclos(referencia.ciclos);
        setPorNivel(mapa);
      } catch (error) {
        // silencioso: é a vitrine pública e o preço mensal já está na tela pela configuração.
        // Um aviso de erro aqui assustaria o visitante por algo que ele nem percebeu faltar.
        console.error('Erro ao carregar ciclos de cobrança:', error);
      }
    })();
    return () => { ativo = false; };
  }, []);

  const infoDe = (nivel) => porNivel[nivel]?.[ciclo];

  return (
    <div className="space-y-6">
      {ciclos.length > 0 && (
        <div className="flex flex-wrap justify-center gap-2" data-testid="seletor-ciclo-precos">
          {ciclos.map((c) => (
            <button
              key={c.ciclo}
              onClick={() => setCiclo(c.ciclo)}
              data-testid={`ciclo-precos-${c.ciclo}`}
              className={`px-4 py-2 rounded-full text-sm font-medium border transition ${
                ciclo === c.ciclo
                  ? 'bg-primary text-white border-primary'
                  : isDark
                  ? 'border-slate-700 text-slate-300 hover:border-primary'
                  : 'border-slate-300 text-slate-700 hover:border-primary'
              }`}
            >
              {c.rotulo}
              {c.meses_gratis > 0 && (
                <span className={`ml-2 text-xs font-bold ${ciclo === c.ciclo ? 'text-white' : 'text-emerald-600 dark:text-emerald-400'}`}>
                  {c.meses_gratis} {c.meses_gratis === 1 ? 'mês' : 'meses'} grátis
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6" data-testid="precos-grid">
        <PlanCard
          nome="Básico"
          preco={config.plano_basico_preco ?? 97}
          ciclo={infoDe('basico')}
          clientes={config.plano_basico_clientes ?? 50}
          emprestimos={config.plano_basico_emprestimos ?? 100}
          extras={['Cobrança PIX e WhatsApp', 'Relatórios básicos', 'Suporte por e-mail']}
          isDark={isDark}
        />
        <PlanCard
          nome="Profissional"
          preco={config.plano_profissional_preco ?? 197}
          ciclo={infoDe('profissional')}
          clientes={config.plano_profissional_clientes ?? 200}
          emprestimos={config.plano_profissional_emprestimos ?? 500}
          extras={['Régua de cobrança automática', 'Contratos digitais (CCB)', 'Relatórios avançados', 'Portal do cliente']}
          popular
          isDark={isDark}
        />
        <PlanCard
          nome="Empresarial"
          preco={config.plano_enterprise_preco ?? 497}
          ciclo={infoDe('enterprise')}
          clientes={config.plano_enterprise_clientes ?? -1}
          emprestimos={config.plano_enterprise_emprestimos ?? -1}
          extras={['Recursos ilimitados', 'Score e análise de risco', 'Assistente com IA', 'Suporte prioritário']}
          isDark={isDark}
        />
      </div>

      {ciclo !== 'mensal' && (
        <p className={`text-center text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
          Pagamento único por PIX cobrindo todo o período. O teste grátis continua sem cartão.
        </p>
      )}
    </div>
  );
};

const Precos = () => (
  <CommercialLanding
    seo={{
      title: 'Preços e planos do Kredor | Gestão de empréstimos',
      description: 'Conheça os planos do Kredor para gestão de empréstimos e cobrança. Comece com 7 dias grátis, sem cartão de crédito. Cancele quando quiser.',
      path: '/precos',
    }}
    eyebrow="Planos e preços"
    h1="Planos do Kredor para cada tamanho de carteira"
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
    {({ config, isDark }) => <GradePlanos config={config} isDark={isDark} />}
  </CommercialLanding>
);

export default Precos;
