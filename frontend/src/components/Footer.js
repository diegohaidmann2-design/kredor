import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Facebook,
  Instagram,
  Linkedin,
  MessageCircle,
  Mail,
  Phone,
  MapPin
} from 'lucide-react';

const Footer = ({ config, isDark = true }) => {
  const currentYear = new Date().getFullYear();
  
  const whatsappLink = config?.whatsapp_numero 
    ? `https://wa.me/55${config.whatsapp_numero.replace(/\D/g, '')}?text=${encodeURIComponent(config?.whatsapp_mensagem || 'Olá! Gostaria de saber mais sobre o Gestor Cred.')}`
    : null;

  const footerLinks = {
    produto: [
      { label: 'Funcionalidades', href: '/#funcionalidades' },
      { label: 'Preços', href: '/#planos' },
      { label: 'Como Funciona', to: '/como-funciona' },
      { label: 'FAQ', to: '/faq' },
    ],
    empresa: [
      { label: 'Sobre Nós', to: '/sobre' },
      { label: 'Contato', to: '/contato' },
      { label: 'Blog', href: '#' },
    ],
    legal: [
      { label: 'Termos de Uso', to: '/termos' },
      { label: 'Política de Privacidade', to: '/privacidade' },
    ],
  };

  const socialLinks = [
    { icon: Facebook, href: '#', label: 'Facebook' },
    { icon: Instagram, href: '#', label: 'Instagram' },
    { icon: Linkedin, href: '#', label: 'LinkedIn' },
  ];

  const LinkItem = ({ item }) => {
    if (item.to) {
      return (
        <Link 
          to={item.to} 
          className={`text-sm transition-colors ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}
        >
          {item.label}
        </Link>
      );
    }
    return (
      <a 
        href={item.href} 
        className={`text-sm transition-colors ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}
      >
        {item.label}
      </a>
    );
  };

  return (
    <footer className={`${isDark ? 'bg-slate-900 border-slate-800' : 'bg-slate-100 border-slate-200'} border-t`}>
      {/* Main Footer */}
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8">
          {/* Brand Column */}
          <div className="lg:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-emerald-600 flex items-center justify-center shadow-glow">
                <span className="text-lg font-display font-bold text-white">JF</span>
              </div>
              <span className="text-xl font-display font-bold">
                <span className="text-primary">Juro</span>
                <span className={isDark ? 'text-white' : 'text-slate-900'}>Fácil</span>
              </span>
            </div>
            <p className={`text-sm mb-6 max-w-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
              {config?.descricao || 'Sistema completo para gestão de empréstimos. Controle seus clientes, parcelas e pagamentos de forma simples e profissional.'}
            </p>
            
            {/* Contact Info */}
            <div className="space-y-2">
              {config?.email && (
                <a href={`mailto:${config.email}`} className={`flex items-center gap-2 text-sm ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}>
                  <Mail className="w-4 h-4" />
                  {config.email}
                </a>
              )}
              {config?.whatsapp_numero && (
                <a href={whatsappLink} target="_blank" rel="noopener noreferrer" className={`flex items-center gap-2 text-sm ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}>
                  <Phone className="w-4 h-4" />
                  {config.whatsapp_numero}
                </a>
              )}
            </div>
          </div>

          {/* Product Links */}
          <div>
            <h4 className={`font-semibold mb-4 ${isDark ? 'text-white' : 'text-slate-900'}`}>Produto</h4>
            <ul className="space-y-3">
              {footerLinks.produto.map((item, i) => (
                <li key={i}><LinkItem item={item} /></li>
              ))}
            </ul>
          </div>

          {/* Company Links */}
          <div>
            <h4 className={`font-semibold mb-4 ${isDark ? 'text-white' : 'text-slate-900'}`}>Empresa</h4>
            <ul className="space-y-3">
              {footerLinks.empresa.map((item, i) => (
                <li key={i}><LinkItem item={item} /></li>
              ))}
            </ul>
          </div>

          {/* Legal Links */}
          <div>
            <h4 className={`font-semibold mb-4 ${isDark ? 'text-white' : 'text-slate-900'}`}>Legal</h4>
            <ul className="space-y-3">
              {footerLinks.legal.map((item, i) => (
                <li key={i}><LinkItem item={item} /></li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className={`border-t ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
        <div className="container mx-auto px-4 py-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            {/* Copyright */}
            <p className={`text-sm ${isDark ? 'text-slate-500' : 'text-slate-600'}`}>
              © {currentYear} Gestor Cred. Todos os direitos reservados.
            </p>

            {/* Social Links */}
            <div className="flex items-center gap-4">
              {socialLinks.map((social, i) => (
                <motion.a
                  key={i}
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`p-2 rounded-lg transition-colors ${isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'}`}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  aria-label={social.label}
                >
                  <social.icon className="w-5 h-5" />
                </motion.a>
              ))}
              {whatsappLink && (
                <motion.a
                  href={whatsappLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 rounded-lg text-green-500 hover:text-green-400 hover:bg-green-500/10 transition-colors"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  aria-label="WhatsApp"
                >
                  <MessageCircle className="w-5 h-5" />
                </motion.a>
              )}
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
