import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Mail, Phone, MapPin, Send, MessageCircle, Clock } from 'lucide-react';
import Footer from '../components/Footer';
import SiteHeader from '../components/SiteHeader';
import { useTheme } from '../context/ThemeContext';
import { configuracoesAPI } from '../api/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';

const Contato = () => {
  const [config, setConfig] = useState({});
  const { isDark } = useTheme();
  const [formData, setFormData] = useState({ nome: '', email: '', assunto: '', mensagem: '' });
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await configuracoesAPI.obterLanding();
        setConfig(res.data);
      } catch (e) {}
    };
    loadConfig();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setEnviando(true);
    // Simular envio
    await new Promise(r => setTimeout(r, 1500));
    setEnviado(true);
    setEnviando(false);
  };

  const whatsappLink = config?.whatsapp 
    ? `https://wa.me/55${config.whatsapp.replace(/\D/g, '')}?text=${encodeURIComponent('Olá! Vim pelo site e gostaria de mais informações.')}`
    : null;

  const contactInfo = [
    { icon: Mail, label: 'E-mail', value: 'contato@kredor.com.br', href: 'mailto:contato@kredor.com.br' },
    { icon: Phone, label: 'WhatsApp', value: config?.whatsapp || '(11) 99999-9999', href: whatsappLink },
    { icon: Clock, label: 'Horário', value: 'Seg-Sex: 9h às 18h', href: null },
    { icon: MapPin, label: 'Localização', value: 'São Paulo, SP - Brasil', href: null }
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
          className="text-center mb-12"
        >
          <h1 className="text-3xl md:text-4xl font-display font-bold mb-4">Entre em Contato</h1>
          <p className={`text-lg ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            Estamos aqui para ajudar. Escolha a melhor forma de falar conosco.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 max-w-6xl mx-auto">
          {/* Contact Info */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            <h2 className="text-2xl font-semibold mb-6">Informações de Contato</h2>
            <div className="space-y-4 mb-8">
              {contactInfo.map((item, index) => (
                <div key={index} className={`flex items-center gap-4 p-4 rounded-xl ${isDark ? 'bg-slate-800/50' : 'bg-slate-50'}`}>
                  <div className="p-3 rounded-xl bg-primary/10">
                    <item.icon className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{item.label}</p>
                    {item.href ? (
                      <a href={item.href} target="_blank" rel="noopener noreferrer" className="font-medium hover:text-primary transition-colors">
                        {item.value}
                      </a>
                    ) : (
                      <p className="font-medium">{item.value}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {whatsappLink && (
              <a href={whatsappLink} target="_blank" rel="noopener noreferrer">
                <Button className="w-full bg-green-600 hover:bg-green-700 text-white">
                  <MessageCircle className="w-5 h-5 mr-2" />
                  Conversar no WhatsApp
                </Button>
              </a>
            )}
          </motion.div>

          {/* Contact Form */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
          >
            <h2 className="text-2xl font-semibold mb-6">Envie uma Mensagem</h2>
            
            {enviado ? (
              <div className={`p-8 rounded-2xl text-center ${isDark ? 'bg-slate-800/50' : 'bg-slate-50'}`}>
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <Send className="w-8 h-8 text-primary" />
                </div>
                <h3 className="text-xl font-semibold mb-2">Mensagem Enviada!</h3>
                <p className={isDark ? 'text-slate-400' : 'text-slate-600'}>
                  Obrigado pelo contato. Responderemos em breve.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>Nome</label>
                  <Input
                    type="text"
                    value={formData.nome}
                    onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                    required
                    className={`${isDark ? 'bg-slate-800 border-slate-700' : ''}`}
                    placeholder="Seu nome completo"
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>E-mail</label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                    className={`${isDark ? 'bg-slate-800 border-slate-700' : ''}`}
                    placeholder="seu@email.com"
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>Assunto</label>
                  <Input
                    type="text"
                    value={formData.assunto}
                    onChange={(e) => setFormData({ ...formData, assunto: e.target.value })}
                    required
                    className={`${isDark ? 'bg-slate-800 border-slate-700' : ''}`}
                    placeholder="Sobre o que deseja falar?"
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>Mensagem</label>
                  <textarea
                    value={formData.mensagem}
                    onChange={(e) => setFormData({ ...formData, mensagem: e.target.value })}
                    required
                    rows={5}
                    className={`w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary ${isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white border-slate-300'}`}
                    placeholder="Escreva sua mensagem..."
                  />
                </div>
                <Button type="submit" disabled={enviando} className="w-full bg-primary hover:bg-primary/90">
                  {enviando ? 'Enviando...' : 'Enviar Mensagem'}
                  <Send className="w-4 h-4 ml-2" />
                </Button>
              </form>
            )}
          </motion.div>
        </div>
      </main>

      <Footer config={config} isDark={isDark} />
    </div>
  );
};

export default Contato;
