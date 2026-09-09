import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, FileText, CheckCircle, AlertTriangle, Ban, Scale, RefreshCw } from 'lucide-react';
import Footer from '../components/Footer';
import { configuracoesAPI } from '../api/api';

const TermosUso = () => {
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
      icon: CheckCircle,
      title: '1. Aceitação dos Termos',
      content: `Ao acessar e utilizar a plataforma Kredor, você concorda com estes Termos de Uso. Se você não concordar com qualquer parte destes termos, não deverá utilizar nossos serviços.\n\nEstes termos podem ser atualizados periodicamente, e é sua responsabilidade revisá-los regularmente.`
    },
    {
      icon: FileText,
      title: '2. Descrição do Serviço',
      content: `O Kredor é uma plataforma de gestão de empréstimos que oferece:\n• Cadastro e gestão de clientes\n• Controle de empréstimos com diferentes métodos de cálculo\n• Geração de contratos e relatórios\n• Simulador de empréstimos\n• Controle de pagamentos e parcelas\n• Notificações e lembretes`
    },
    {
      icon: AlertTriangle,
      title: '3. Responsabilidades do Usuário',
      content: `Ao utilizar o Kredor, você se compromete a:\n• Fornecer informações verdadeiras e atualizadas\n• Manter a confidencialidade de suas credenciais\n• Utilizar o sistema apenas para fins legais\n• Não compartilhar sua conta com terceiros\n• Respeitar as leis aplicáveis ao seu negócio\n• Manter backup dos seus dados importantes`
    },
    {
      icon: Ban,
      title: '4. Uso Proibido',
      content: `É expressamente proibido:\n• Utilizar o sistema para atividades ilegais\n• Cobrar juros abusivos ou realizar cobranças ilícitas\n• Tentar acessar dados de outros usuários\n• Realizar engenharia reversa do sistema\n• Sobrecarregar nossos servidores intencionalmente\n• Violar direitos de propriedade intelectual`
    },
    {
      icon: Scale,
      title: '5. Limitação de Responsabilidade',
      content: `O Kredor:\n• Não é responsável por decisões financeiras tomadas pelo usuário\n• Não garante resultados específicos no seu negócio\n• Não se responsabiliza por perdas decorrentes de uso indevido\n• Não oferece assessoria jurídica ou financeira\n• Pode sofrer interrupções para manutenção\n\nO uso do sistema é por sua conta e risco.`
    },
    {
      icon: RefreshCw,
      title: '6. Cancelamento e Reembolso',
      content: `Política de cancelamento:\n• Você pode cancelar sua assinatura a qualquer momento\n• O acesso permanece até o fim do período pago\n• Não há reembolso proporcional para cancelamentos\n• Dados podem ser exportados antes do cancelamento\n• Após 30 dias do cancelamento, dados serão excluídos\n\nPara cancelar, acesse Configurações > Assinatura.`
    }
  ];

  return (
    <div className={`min-h-screen ${isDark ? 'bg-slate-950 text-white' : 'bg-white text-slate-900'}`}>
      {/* Header */}
      <header className={`sticky top-0 z-40 backdrop-blur-xl border-b ${isDark ? 'bg-slate-950/80 border-slate-800' : 'bg-white/80 border-slate-200'}`}>
        <nav className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-emerald-600 flex items-center justify-center">
              <span className="text-lg font-display font-bold text-white">GC</span>
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
          className="max-w-4xl mx-auto"
        >
          <div className="text-center mb-12">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-2xl mb-4">
              <FileText className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-3xl md:text-4xl font-display font-bold mb-4">Termos de Uso</h1>
            <p className={`text-lg ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
              Última atualização: Janeiro de 2025
            </p>
          </div>

          <div className={`prose max-w-none mb-12 ${isDark ? 'prose-invert' : ''}`}>
            <p className={`text-lg ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
              Bem-vindo ao Kredor. Estes Termos de Uso regulam a utilização de nossa plataforma de gestão de empréstimos. Por favor, leia atentamente antes de utilizar nossos serviços.
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

export default TermosUso;
