import React from 'react';
import { motion } from 'framer-motion';
import { Star, Quote } from 'lucide-react';
import fotoRicardo from '../assets/testimonials/ricardo.jpg';
import fotoFernanda from '../assets/testimonials/fernanda.jpg';
import fotoMarcos from '../assets/testimonials/marcos.jpg';

/**
 * 💬 DEPOIMENTOS
 * Substitua pelos depoimentos reais dos seus clientes (nome, negócio, cidade e texto).
 * Para foto, aponte `foto` para a imagem do cliente.
 */
const TESTIMONIALS = [
  {
    nome: 'Ricardo Almeida',
    cargo: 'Crédito pessoal • São Paulo/SP',
    foto: fotoRicardo,
    texto: 'Reduzi minha inadimplência em mais de 30% no primeiro mês. A régua de cobrança no WhatsApp com o PIX já dentro da mensagem mudou meu jogo.',
    nota: 5,
  },
  {
    nome: 'Fernanda Costa',
    cargo: 'Microcrédito • Belo Horizonte/MG',
    foto: fotoFernanda,
    texto: 'Antes eu controlava tudo em planilha e vivia perdido. Hoje vejo a carteira inteira no dashboard e sei exatamente quem está atrasado e quanto tenho a receber.',
    nota: 5,
  },
  {
    nome: 'Marcos Oliveira',
    cargo: 'Financiamento particular • Curitiba/PR',
    foto: fotoMarcos,
    texto: 'A consulta de CPF direto na plataforma me poupa tempo e evita calote. Aprovo com muito mais segurança e o portal do cliente diminuiu as ligações de cobrança.',
    nota: 5,
  },
];

const initials = (nome) => nome.split(' ').slice(0, 2).map((n) => n[0]).join('').toUpperCase();

const Testimonials = ({ isDark = true }) => {
  const cardBg = isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200';
  const muted = isDark ? 'text-slate-400' : 'text-slate-500';

  return (
    <section id="depoimentos" className={`py-20 ${isDark ? 'bg-slate-900/40' : 'bg-slate-50'}`}>
      <div className="container mx-auto px-4">
        <motion.div className="text-center mb-12" initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-4">
            <Star className="w-3 h-3 fill-current" /> Depoimentos
          </span>
          <h2 className="text-3xl md:text-4xl font-display font-bold mb-3">O que dizem nossos clientes</h2>
          <p className={`text-lg ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            Credores que profissionalizaram a gestão e reduziram a inadimplência com o GestorCred
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {TESTIMONIALS.map((t, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }} transition={{ delay: i * 0.12 }}
              data-testid={`testimonial-card-${i}`}
              className={`relative rounded-2xl border p-6 ${cardBg} transition-all hover:shadow-lg hover:shadow-primary/5`}>
              <Quote className="w-8 h-8 text-primary/25 mb-3" />
              <div className="flex gap-0.5 mb-3">
                {Array.from({ length: t.nota }).map((_, s) => (
                  <Star key={s} className="w-4 h-4 text-amber-400 fill-amber-400" />
                ))}
              </div>
              <p className={`text-sm leading-relaxed mb-6 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                “{t.texto}”
              </p>
              <div className="flex items-center gap-3">
                {t.foto ? (
                  <img src={t.foto} alt={t.nome} loading="lazy" width={44} height={44} className="w-11 h-11 rounded-full object-cover" />
                ) : (
                  <div className="w-11 h-11 rounded-full bg-gradient-to-br from-primary to-emerald-600 flex items-center justify-center text-white text-sm font-bold">
                    {initials(t.nome)}
                  </div>
                )}
                <div>
                  <p className="text-sm font-semibold">{t.nome}</p>
                  <p className={`text-xs ${muted}`}>{t.cargo}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div className={`flex flex-wrap items-center justify-center gap-x-10 gap-y-4 mt-12 text-center`}
          initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}>
          {[
            { v: '4.9/5', l: 'Avaliação média' },
            { v: '-32%', l: 'Inadimplência' },
            { v: '+2.5h', l: 'Economia por dia' },
            { v: '100%', l: 'Dados criptografados' },
          ].map((m, i) => (
            <div key={i}>
              <p className="text-2xl md:text-3xl font-display font-bold text-primary">{m.v}</p>
              <p className={`text-xs ${muted}`}>{m.l}</p>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};

export default Testimonials;
