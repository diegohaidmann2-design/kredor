import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import logomark from '../assets/logomark.png';
import {
  Facebook,
  Instagram,
  Linkedin,
  Youtube,
  MessageCircle,
  Mail,
  Phone,
  MapPin,
  ShieldCheck
} from 'lucide-react';

const Footer = ({ config, isDark = true }) => {
  const currentYear = new Date().getFullYear();
  
  const whatsappLink = config?.whatsapp_numero 
    ? `https://wa.me/55${config.whatsapp_numero.replace(/\D/g, '')}?text=${encodeURIComponent(config?.whatsapp_mensagem || 'Olá! Gostaria de saber mais sobre o Kredor.')}`
    : null;

  const footerLinks = {
    produto: [
      { label: 'Funcionalidades', href: '/#funcionalidades' },
      { label: 'Preços', to: '/precos' },
      { label: 'Como Funciona', to: '/como-funciona' },
      { label: 'FAQ', to: '/faq' },
    ],
    solucoes: [
      { label: 'Gestão de empréstimos', to: '/sistema-gestao-emprestimos' },
      { label: 'Cobrança no WhatsApp', to: '/cobranca-whatsapp' },
      { label: 'Cobrança PIX', to: '/cobranca-pix' },
      { label: 'Parcelas e juros', to: '/controle-de-parcelas-e-juros' },
      { label: 'Gestão de clientes', to: '/gestao-de-clientes' },
    ],
    empresa: [
      { label: 'Sobre Nós', to: '/sobre' },
      { label: 'Contato', to: '/contato' },
      { label: 'Blog', href: '#' },
    ],
    legal: [
      { label: 'Termos de Uso', to: '/termos' },
      { label: 'LGPD / Privacidade', to: '/privacidade' },
      { label: 'Segurança', to: '/seguranca' },
    ],
  };

  const socialLinks = [
    { icon: Facebook, href: config?.social_facebook, label: 'Facebook' },
    { icon: Instagram, href: config?.social_instagram, label: 'Instagram' },
    { icon: Linkedin, href: config?.social_linkedin, label: 'LinkedIn' },
    { icon: Youtube, href: config?.social_youtube, label: 'YouTube' },
  ].filter((s) => s.href && s.href.trim());

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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-8">
          {/* Brand Column */}
          <div className="lg:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <img src={logomark} alt="Kredor" className="w-10 h-10 object-contain" />
              <span className="text-xl font-display font-bold">
                <span className="text-primary">Kredor</span>
              </span>
            </div>
            <p className={`text-sm mb-6 max-w-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
              {config?.descricao || 'Sistema completo para gestão de empréstimos. Controle seus clientes, parcelas e pagamentos de forma simples e profissional.'}
            </p>
            
            {/* Contact Info */}
            <div className="space-y-2">
              {(config?.email_suporte || config?.email) && (
                <a href={`mailto:${config.email_suporte || config.email}`} className={`flex items-center gap-2 text-sm ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}>
                  <Mail className="w-4 h-4" />
                  {config.email_suporte || config.email}
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

          {/* Solution Links */}
          <div>
            <h4 className={`font-semibold mb-4 ${isDark ? 'text-white' : 'text-slate-900'}`}>Soluções</h4>
            <ul className="space-y-3">
              {footerLinks.solucoes.map((item, i) => (
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
          <p className={`text-xs mb-4 text-center md:text-left ${isDark ? 'text-slate-500' : 'text-slate-500'}`} data-testid="footer-disclaimer">
            Kredor é um software de gestão. Não concede empréstimos nem realiza operações de crédito.
          </p>
          <div className="flex justify-center md:justify-start mb-4">
            <span
              className={`inline-flex items-center gap-2 text-xs font-medium rounded-full px-3 py-1 ${isDark ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'}`}
              data-testid="footer-selo-seguranca"
            >
              <ShieldCheck className="w-4 h-4" />
              Dados criptografados
            </span>
          </div>
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            {/* Copyright */}
            <div className={`text-sm text-center md:text-left ${isDark ? 'text-slate-500' : 'text-slate-600'}`}>
              <p data-testid="footer-copyright">© {currentYear} {config?.nome_empresa || 'Kredor'}. Todos os direitos reservados.</p>
              {(config?.razao_social || config?.cnpj || config?.email_suporte) && (
                <p className="text-xs mt-1" data-testid="footer-company">
                  {[
                    config?.razao_social,
                    config?.cnpj ? `CNPJ ${config.cnpj}` : null,
                    config?.endereco,
                    config?.email_suporte ? `Suporte: ${config.email_suporte}` : null,
                  ].filter(Boolean).join(' • ')}
                </p>
              )}
            </div>

            {/* Social Links */}
            {(socialLinks.length > 0 || whatsappLink) && (
            <div className="flex items-center gap-4" data-testid="footer-social">
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
            )}
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
