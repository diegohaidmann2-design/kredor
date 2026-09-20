import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, HelpCircle, ChevronDown, Search } from 'lucide-react';
import Footer from '../components/Footer';
import { configuracoesAPI } from '../api/api';
import JsonLd from '../components/JsonLd';
import useSeo from '../hooks/useSeo';
import { faqPageSchema, breadcrumbSchema } from '../lib/seoSchema';

const FAQ = () => {
  const [config, setConfig] = useState({});
  const [isDark, setIsDark] = useState(true);
  const [openIndex, setOpenIndex] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await configuracoesAPI.obterLanding();
        setConfig(res.data);
      } catch (e) {}
    };
    loadConfig();
    setIsDark(localStorage.getItem('sgej-theme') !== 'light');
  }, []);

  const faqs = [
    {
      category: 'Geral',
      questions: [
        { q: 'O que é o Kredor?', a: 'O Kredor é uma plataforma completa para gestão de empréstimos. Com ele, você pode cadastrar clientes, registrar empréstimos, gerar contratos, controlar pagamentos e muito mais.' },
        { q: 'O Kredor substitui a planilha e o caderninho?', a: 'Sim. Ele centraliza clientes, empréstimos, parcelas e recebimentos com cálculo automático e cobrança integrada — mais seguro e organizado do que planilhas ou anotações em papel.' },
        { q: 'Preciso instalar algum programa?', a: 'Não! O Kredor funciona 100% online, diretamente no seu navegador. Basta criar uma conta e começar a usar. Funciona em computador, tablet e celular.' },
        { q: 'Meus dados estão seguros?', a: 'Sim! Utilizamos criptografia SSL/TLS em todas as comunicações, senhas são armazenadas com hash seguro, e fazemos backups diários. Seguimos as normas da LGPD.' }
      ]
    },
    {
      category: 'Funcionalidades',
      questions: [
        { q: 'Quais métodos de cálculo estão disponíveis?', a: 'Oferecemos 4 métodos: Juros Simples, Juros Compostos, Tabela Price e SAC (Sistema de Amortização Constante). Você pode simular e comparar antes de registrar.' },
        { q: 'Quais frequências de pagamento o sistema aceita?', a: 'Diário, semanal, quinzenal e mensal, com regras de dias (úteis, seg-sex ou todos os dias) para gerar os vencimentos do jeito que você trabalha.' },
        { q: 'O sistema aplica multa e juros por atraso?', a: 'Sim. Você define a multa e os juros de mora e o Kredor calcula automaticamente o valor atualizado das parcelas em atraso.' },
        { q: 'Posso gerar contratos?', a: 'Sim! O sistema gera contratos profissionais em PDF com todos os dados do empréstimo preenchidos automaticamente. Basta clicar em "Gerar Contrato".' },
        { q: 'Como funciona o controle de pagamentos?', a: 'Você pode registrar cada pagamento recebido, e o sistema atualiza automaticamente o status das parcelas. Também enviamos alertas de vencimentos próximos.' }
      ]
    },
    {
      category: 'Cobrança e recebimento',
      questions: [
        { q: 'O Kredor cobra meus clientes automaticamente?', a: 'Sim. Você monta uma régua de cobrança e o sistema envia lembretes antes do vencimento e avisos de atraso por WhatsApp, sem você precisar ligar ou mandar mensagem manualmente.' },
        { q: 'Como funciona a cobrança por PIX?', a: 'Cada parcela pode gerar um PIX (QR Code e copia e cola). Quando o cliente paga, a baixa é reconhecida automaticamente e a parcela é marcada como recebida, sem conferência manual.' },
        { q: 'Consigo consultar o CPF do cliente antes de emprestar?', a: 'Sim. É possível consultar dados e a situação do CPF no momento do cadastro para apoiar a sua análise de crédito e reduzir o risco de inadimplência.' },
        { q: 'Existe um portal para o cliente acompanhar as parcelas?', a: 'Sim. O cliente acessa um portal para ver parcelas, valores e datas e realizar pagamentos por autoatendimento, reduzindo ligações e atritos na cobrança.' }
      ]
    },
    {
      category: 'Planos e Pagamento',
      questions: [
        { q: 'Existe período de teste grátis?', a: 'Sim! Oferecemos 7 dias de teste grátis com acesso a todas as funcionalidades básicas. Não pedimos cartão de crédito para começar.' },
        { q: 'Quais formas de pagamento são aceitas?', a: 'Aceitamos cartão de crédito (via Stripe), PIX e boleto bancário. Os planos são mensais e você pode cancelar a qualquer momento.' },
        { q: 'Posso mudar de plano?', a: 'Sim! Você pode fazer upgrade ou downgrade do seu plano a qualquer momento. A mudança é aplicada imediatamente e o valor é ajustado proporcionalmente.' }
      ]
    },
    {
      category: 'Suporte',
      questions: [
        { q: 'Como entro em contato com o suporte?', a: 'Você pode nos contatar por email, WhatsApp ou pela página de Contato. O horário de atendimento é de segunda a sexta, das 9h às 18h.' },
        { q: 'Vocês oferecem treinamento?', a: 'Sim! Para planos Enterprise, oferecemos treinamento personalizado. Para outros planos, temos tutoriais em vídeo e documentação completa.' },
        { q: 'E se eu tiver problemas técnicos?', a: 'Entre em contato imediatamente pelo suporte. Problemas críticos são tratados com prioridade máxima, geralmente resolvidos em até 4 horas.' }
      ]
    }
  ];

  const filteredFaqs = faqs.map(category => ({
    ...category,
    questions: category.questions.filter(
      faq => faq.q.toLowerCase().includes(searchTerm.toLowerCase()) ||
             faq.a.toLowerCase().includes(searchTerm.toLowerCase())
    )
  })).filter(category => category.questions.length > 0);

  const allFaqItems = faqs.flatMap((c) => c.questions);
  useSeo({
    title: 'Perguntas Frequentes | Kredor',
    description: 'Tire suas dúvidas sobre o Kredor: planos, teste grátis, métodos de cálculo, contratos, segurança e suporte para credores particulares.',
    path: '/faq',
  });

  return (
    <div className={`min-h-screen ${isDark ? 'bg-slate-950 text-white' : 'bg-white text-slate-900'}`}>
      <JsonLd id="faq-page" data={faqPageSchema(allFaqItems)} />
      <JsonLd id="faq-breadcrumb" data={breadcrumbSchema([{ name: 'Perguntas frequentes', path: '/faq' }])} />
      {/* Header */}
      <header className={`sticky top-0 z-40 backdrop-blur-xl border-b ${isDark ? 'bg-slate-950/80 border-slate-800' : 'bg-white/80 border-slate-200'}`}>
        <nav className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-emerald-600 flex items-center justify-center">
              <span className="text-lg font-display font-bold text-white">K</span>
            </div>
            <span className="text-xl font-display font-bold">
              <span className="text-primary">Kredor</span>
            </span>
          </Link>
          <Link to="/" className={`flex items-center gap-2 text-sm ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}>
            <ArrowLeft className="w-4 h-4" />
            Voltar
          </Link>
        </nav>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-2xl mb-4">
            <HelpCircle className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl md:text-4xl font-display font-bold mb-4">Perguntas Frequentes</h1>
          <p className={`text-lg mb-8 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            Encontre respostas para as dúvidas mais comuns
          </p>
          
          {/* Search */}
          <div className="max-w-md mx-auto relative">
            <Search className={`absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 ${isDark ? 'text-slate-500' : 'text-slate-400'}`} />
            <input
              type="text"
              placeholder="Buscar pergunta..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={`w-full pl-12 pr-4 py-3 rounded-xl border focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary ${isDark ? 'bg-slate-800 border-slate-700 text-white placeholder-slate-500' : 'bg-white border-slate-300'}`}
            />
          </div>
        </motion.div>

        <div className="max-w-3xl mx-auto space-y-8">
          {filteredFaqs.map((category, catIndex) => (
            <motion.div
              key={catIndex}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: catIndex * 0.1 }}
            >
              <h2 className="text-xl font-semibold mb-4 text-primary">{category.category}</h2>
              <div className="space-y-3">
                {category.questions.map((faq, index) => {
                  const globalIndex = `${catIndex}-${index}`;
                  const isOpen = openIndex === globalIndex;
                  
                  return (
                    <div
                      key={index}
                      className={`rounded-xl overflow-hidden ${isDark ? 'bg-slate-800/50 border border-slate-700' : 'bg-slate-50 border border-slate-200'}`}
                    >
                      <button
                        onClick={() => setOpenIndex(isOpen ? null : globalIndex)}
                        className="w-full flex items-center justify-between p-4 text-left"
                      >
                        <span className="font-medium pr-4">{faq.q}</span>
                        <ChevronDown className={`w-5 h-5 flex-shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''} ${isDark ? 'text-slate-400' : 'text-slate-500'}`} />
                      </button>
                      <AnimatePresence>
                        {isOpen && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                          >
                            <div className={`px-4 pb-4 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                              {faq.a}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          ))}
        </div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mt-16"
        >
          <p className={`mb-4 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            Não encontrou sua resposta?
          </p>
          <Link to="/contato" className="text-primary hover:underline font-medium">
            Entre em contato conosco →
          </Link>
        </motion.div>
      </main>

      <Footer config={config} isDark={isDark} />
    </div>
  );
};

export default FAQ;
