import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Shield, Lock, Eye, Database, UserCheck, Mail } from 'lucide-react';
import Footer from '../components/Footer';
import SiteHeader from '../components/SiteHeader';
import { useTheme } from '../context/ThemeContext';
import { configuracoesAPI } from '../api/api';

const PoliticaPrivacidade = () => {
  const [config, setConfig] = useState({});
  const { isDark } = useTheme();

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await configuracoesAPI.obterLanding();
        setConfig(res.data);
      } catch (e) {}
    };
    loadConfig();
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
• E-mail: privacidade@kredor.com.br
• Ou através da página de Contato em nosso site

Responderemos sua solicitação em até 15 dias úteis.`
    }
  ];

  return (
    <div className={`min-h-screen ${isDark ? 'bg-slate-950 text-white' : 'bg-white text-slate-900'}`}>
      {/* Header unificado */}
      <SiteHeader />

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
              A Kredor está comprometida com a proteção da sua privacidade. Esta política descreve como coletamos, usamos e protegemos suas informações pessoais em conformidade com a Lei Geral de Proteção de Dados (LGPD).
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
