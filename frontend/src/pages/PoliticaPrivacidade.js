import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Shield, Lock, Eye, Database, UserCheck, Mail } from 'lucide-react';
import Footer from '../components/Footer';
import { configuracoesAPI } from '../api/api';

const PoliticaPrivacidade = () => {
  const [config, setConfig] = useState({});
  const [isDark, setIsDark] = useState(true);

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

  const sections = [
    {
      icon: Database,
      title: '1. Dados Coletados',
      content: `Coletamos os seguintes dados pessoais:
• Nome completo e CPF/CNPJ para identificação
• E-mail e telefone para comunicação
• Endereço para geração de contratos
• Dados financeiros relacionados aos empréstimos
• Informações de acesso (IP, navegador, dispositivo)`
    },
    {
      icon: Eye,
      title: '2. Uso dos Dados',
      content: `Utilizamos seus dados para:
• Prestação dos serviços contratados
• Geração de relatórios e contratos
• Comunicação sobre sua conta e serviços
• Melhoria contínua da plataforma
• Cumprimento de obrigações legais`
    },
    {
      icon: Lock,
      title: '3. Proteção dos Dados',
      content: `Implementamos medidas de segurança:
• Criptografia SSL/TLS em todas as comunicações
• Senhas armazenadas com hash bcrypt
• Backups regulares e redundantes
• Acesso restrito aos dados por funcionários autorizados
• Monitoramento contínuo de segurança`
    },
    {
      icon: UserCheck,
      title: '4. Seus Direitos (LGPD)',
      content: `Conforme a Lei Geral de Proteção de Dados, você tem direito a:
• Confirmar a existência de tratamento de dados
• Acessar seus dados pessoais
• Corrigir dados incompletos ou desatualizados
• Solicitar anonimização ou bloqueio de dados
• Solicitar a eliminação dos dados
• Revogar consentimento a qualquer momento`
    },
    {
      icon: Shield,
      title: '5. Compartilhamento',
      content: `Seus dados podem ser compartilhados com:
• Processadores de pagamento (Stripe, etc.) para cobrança
• Serviços de infraestrutura (hospedagem, backup)
• Autoridades quando exigido por lei

Não vendemos ou compartilhamos seus dados com terceiros para fins de marketing.`
    },
    {
      icon: Mail,
      title: '6. Contato',
      content: `Para exercer seus direitos ou esclarecer dúvidas sobre privacidade:
• E-mail: privacidade@gestorcred.cloud
• Ou através da página de Contato em nosso site

Responderemos sua solicitação em até 15 dias úteis.`
    }
  ];

  return (
    <div className={`min-h-screen ${isDark ? 'bg-slate-950 text-white' : 'bg-white text-slate-900'}`}>
      {/* Header */}
      <header className={`sticky top-0 z-40 backdrop-blur-xl border-b ${isDark ? 'bg-slate-950/80 border-slate-800' : 'bg-white/80 border-slate-200'}`}>
        <nav className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-emerald-600 flex items-center justify-center">
              <span className="text-lg font-display font-bold text-white">JF</span>
            </div>
            <span className="text-xl font-display font-bold">
              <span className="text-primary">Juro</span>Fácil
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
          className="max-w-4xl mx-auto"
        >
          <div className="text-center mb-12">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-2xl mb-4">
              <Shield className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-3xl md:text-4xl font-display font-bold mb-4">Política de Privacidade</h1>
            <p className={`text-lg ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
              Última atualização: Janeiro de 2025
            </p>
          </div>

          <div className={`prose max-w-none mb-12 ${isDark ? 'prose-invert' : ''}`}>
            <p className={`text-lg ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
              A Gestor Cred está comprometida com a proteção da sua privacidade. Esta política descreve como coletamos, usamos e protegemos suas informações pessoais em conformidade com a Lei Geral de Proteção de Dados (LGPD).
            </p>
          </div>

          <div className="space-y-8">
            {sections.map((section, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`p-6 rounded-2xl ${isDark ? 'bg-slate-800/50 border border-slate-700' : 'bg-slate-50 border border-slate-200'}`}
              >
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-xl bg-primary/10">
                    <section.icon className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold mb-3">{section.title}</h2>
                    <p className={`whitespace-pre-line ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                      {section.content}
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </main>

      <Footer config={config} isDark={isDark} />
    </div>
  );
};

export default PoliticaPrivacidade;
