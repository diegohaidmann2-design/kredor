"""Seed dos artigos iniciais do blog (idempotente por slug). Conteúdo long-tail
que faz link interno para as landing pages correspondentes."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

NOW = datetime.now(timezone.utc).isoformat()

POSTS = [
    {
        "slug": "como-controlar-emprestimos-sem-planilha",
        "titulo": "Como controlar empréstimos sem planilha (e parar de perder dinheiro)",
        "meta_description": "Veja como controlar empréstimos sem planilha: organize clientes, parcelas e juros, automatize a cobrança e reduza a inadimplência com um sistema próprio.",
        "resumo": "A planilha quebra quando a carteira cresce. Veja um jeito mais seguro de controlar clientes, parcelas e cobranças.",
        "categoria": "Gestão",
        "keyword": "controle de empréstimos planilha",
        "cta_to": "/sistema-gestao-emprestimos",
        "cta_label": "Conhecer o sistema de gestão de empréstimos",
        "capa": "/og-sistema-gestao-emprestimos.jpg",
        "lido_min": 6,
        "conteudo_html": """
<p>Quase todo credor começa com uma planilha. Ela funciona nos primeiros empréstimos, mas quando a carteira cresce a planilha vira um risco: fórmulas quebram, datas se perdem e você descobre tarde demais que uma parcela venceu.</p>
<h2>Por que a planilha te limita</h2>
<ul>
<li><strong>Erros silenciosos:</strong> uma célula sobrescrita muda o saldo sem aviso.</li>
<li><strong>Sem cobrança automática:</strong> você precisa lembrar de avisar cada cliente, um por um.</li>
<li><strong>Sem histórico confiável:</strong> difícil saber o que já foi pago e quando.</li>
<li><strong>Nada de segurança:</strong> um arquivo perdido é a carteira inteira perdida.</li>
</ul>
<h2>O que um sistema resolve</h2>
<p>Um sistema de gestão calcula juros e gera as parcelas automaticamente, mostra o que vence hoje, registra cada pagamento e dá baixa sozinho quando o PIX cai. Em vez de procurar informação, você recebe a informação pronta.</p>
<h2>Passo a passo para sair da planilha</h2>
<ol>
<li>Liste seus empréstimos ativos (cliente, valor, prazo, taxa).</li>
<li>Cadastre cada um no sistema — as parcelas são geradas na hora.</li>
<li>Ative a cobrança automática por PIX e WhatsApp.</li>
<li>Acompanhe a inadimplência pelo painel, não por anotações soltas.</li>
</ol>
<h2>Conclusão</h2>
<p>Controlar empréstimos sem planilha não é luxo: é o que separa uma operação amadora de uma profissional. Quanto antes migrar, menos dinheiro você deixa na mesa.</p>
""",
    },
    {
        "slug": "como-cobrar-cliente-inadimplente-pelo-whatsapp",
        "titulo": "Como cobrar cliente inadimplente pelo WhatsApp (sem constrangimento)",
        "meta_description": "Aprenda como cobrar cliente inadimplente pelo WhatsApp com mensagens educadas, régua automática e PIX na mensagem para receber mais rápido.",
        "resumo": "Cobrar pelo WhatsApp funciona quando é no tom certo, na hora certa e de forma automática. Veja como.",
        "categoria": "Cobrança",
        "keyword": "cobrar inadimplente whatsapp",
        "cta_to": "/cobranca-whatsapp",
        "cta_label": "Ver a régua de cobrança no WhatsApp",
        "capa": "/og-cobranca-whatsapp.jpg",
        "lido_min": 5,
        "conteudo_html": """
<p>O WhatsApp é o canal mais eficiente para cobrar — mas também o que mais gera desgaste quando usado errado. O segredo é combinar tom profissional, timing e automação.</p>
<h2>Regra de ouro: lembrete antes, cobrança depois</h2>
<p>Envie um lembrete amigável <strong>antes</strong> do vencimento e uma mensagem objetiva <strong>depois</strong> do atraso. Cobrar quem ainda nem venceu irrita; cobrar tarde demais vira calote.</p>
<h2>Modelos de mensagem</h2>
<ul>
<li><em>Lembrete:</em> "Olá, {nome}! Sua parcela de {valor} vence em {data}. Aqui está o PIX para facilitar: {link}."</li>
<li><em>No vencimento:</em> "Oi, {nome}, hoje é o vencimento da parcela de {valor}. Pode pagar por aqui: {link}."</li>
<li><em>Após atraso:</em> "{nome}, sua parcela de {valor} venceu em {data}. Consegue regularizar hoje? PIX: {link}."</li>
</ul>
<h2>Por que automatizar</h2>
<p>Fazer isso manualmente para dezenas de clientes é inviável e você acaba esquecendo. Uma <strong>régua de cobrança</strong> dispara as mensagens sozinha, com o PIX embutido, e ainda protege seu número contra bloqueio por spam.</p>
<h2>Conclusão</h2>
<p>Cobrança boa é a que acontece sem você precisar ligar. Com mensagens no tom certo e automação, você recupera crédito e preserva o relacionamento.</p>
""",
    },
    {
        "slug": "como-calcular-juros-de-emprestimo-particular",
        "titulo": "Como calcular juros de empréstimo particular (simples, composto, Price e SAC)",
        "meta_description": "Entenda como calcular juros de empréstimo particular: juros simples, compostos, Tabela Price e SAC, com exemplos e uma calculadora gratuita.",
        "resumo": "Juros simples, composto, Price ou SAC? Entenda cada método com exemplos e calcule na hora.",
        "categoria": "Juros",
        "keyword": "calcular juros empréstimo",
        "cta_to": "/controle-de-parcelas-e-juros",
        "cta_label": "Ver controle de parcelas e juros",
        "capa": "/og-controle-de-parcelas-e-juros.jpg",
        "lido_min": 7,
        "conteudo_html": """
<p>Calcular juros errado é o caminho mais rápido para o prejuízo. Veja os quatro métodos mais usados em empréstimos particulares e quando cada um faz sentido.</p>
<h2>Juros simples</h2>
<p>Incidem só sobre o valor emprestado (principal). Fórmula: <strong>Juros = P × i × n</strong>. Emprestando R$ 1.000 a 5% ao mês por 3 meses: 1000 × 0,05 × 3 = R$ 150 de juros.</p>
<h2>Juros compostos</h2>
<p>Incidem sobre principal + juros acumulados. Montante: <strong>M = P × (1 + i)ⁿ</strong>. Os mesmos R$ 1.000 a 5% por 3 meses viram R$ 1.157,63.</p>
<h2>Tabela Price</h2>
<p>Parcelas <strong>fixas</strong> do começo ao fim. É a mais comum para o cliente porque o valor não muda. A parcela inicial embute mais juros e menos amortização.</p>
<h2>SAC</h2>
<p>Amortização <strong>constante</strong>: as parcelas começam mais altas e vão diminuindo. Você recebe o principal mais rápido e cobra menos juros no total.</p>
<h2>Calcule na hora</h2>
<p>Para não errar conta, use a <a href="/calculadora-de-juros">calculadora de juros gratuita do Kredor</a>: informe valor, taxa e prazo e veja parcela, total e juros em cada método.</p>
<h2>Conclusão</h2>
<p>Escolha o método pensando no seu fluxo de caixa e na clareza para o cliente. E automatize o cálculo para eliminar erros.</p>
""",
    },
    {
        "slug": "modelo-de-contrato-de-emprestimo-ccb",
        "titulo": "Modelo de contrato de empréstimo (CCB): o que não pode faltar",
        "meta_description": "Saiba o que um contrato de empréstimo (CCB) precisa ter para dar segurança à operação e como gerar o documento automaticamente.",
        "resumo": "Um bom contrato protege as duas partes. Veja os itens essenciais de uma CCB e como emitir sem burocracia.",
        "categoria": "Contratos",
        "keyword": "contrato de empréstimo modelo",
        "cta_to": "/contratos-digitais-ccb",
        "cta_label": "Gerar contratos e CCB automaticamente",
        "capa": "/og-image-kredor.jpg",
        "lido_min": 6,
        "conteudo_html": """
<p>Emprestar sem contrato é apostar na boa vontade. Mesmo em valores pequenos, um documento simples evita desentendimentos e dá respaldo à cobrança.</p>
<h2>O que é uma CCB</h2>
<p>A Cédula de Crédito Bancário (CCB) é um título que representa uma promessa de pagamento. É amplamente usada para formalizar empréstimos e facilita a execução da dívida em caso de inadimplência.</p>
<h2>Itens que não podem faltar</h2>
<ul>
<li><strong>Partes:</strong> nome, CPF/CNPJ e endereço do credor e do devedor.</li>
<li><strong>Valor e finalidade</strong> do empréstimo.</li>
<li><strong>Taxa de juros, encargos</strong> de mora e multa por atraso.</li>
<li><strong>Prazo, número de parcelas e datas</strong> de vencimento.</li>
<li><strong>Forma de pagamento</strong> (ex.: PIX).</li>
<li><strong>Assinaturas</strong> e, se possível, testemunhas.</li>
</ul>
<h2>Como emitir sem dor de cabeça</h2>
<p>Redigir contrato a cada empréstimo é trabalhoso e sujeito a erro. O Kredor <a href="/contratos-digitais-ccb">gera a CCB e os recibos automaticamente</a> a partir dos dados do empréstimo, prontos em PDF para enviar pelo WhatsApp.</p>
<h2>Conclusão</h2>
<p>Formalizar é barato e rápido quando é automático — e caro quando falta. Padronize seus contratos e opere com segurança.</p>
<p><em>Este conteúdo é informativo e não substitui orientação jurídica.</em></p>
""",
    },
    {
        "slug": "o-que-e-pix-dinamico-e-como-usar-para-cobrar",
        "titulo": "O que é PIX dinâmico e como usar para cobrar empréstimos",
        "meta_description": "Entenda o que é PIX dinâmico, como ele difere do PIX estático e como usá-lo para cobrar empréstimos com baixa automática.",
        "resumo": "PIX dinâmico gera um código por cobrança e permite baixa automática. Veja como usar na sua operação.",
        "categoria": "PIX",
        "keyword": "pix dinâmico cobrança",
        "cta_to": "/cobranca-pix",
        "cta_label": "Ver cobrança por PIX automática",
        "capa": "/og-cobranca-pix.jpg",
        "lido_min": 5,
        "conteudo_html": """
<p>Se você ainda usa uma única chave PIX para receber de todo mundo, está perdendo tempo com conferência manual. O PIX dinâmico resolve isso.</p>
<h2>PIX estático x dinâmico</h2>
<p>O <strong>estático</strong> é sempre o mesmo código (sua chave), sem valor definido — você precisa conferir cada pagamento no extrato. O <strong>dinâmico</strong> gera um código único por cobrança, já com valor e identificação, permitindo reconhecer automaticamente quem pagou.</p>
<h2>Por que isso muda o jogo</h2>
<ul>
<li><strong>Baixa automática:</strong> o pagamento cai e a parcela é quitada sozinha.</li>
<li><strong>Sem confusão:</strong> cada PIX está amarrado a uma parcela específica.</li>
<li><strong>Cobrança na mensagem:</strong> o código vai dentro do WhatsApp, o cliente paga em segundos.</li>
</ul>
<h2>Como aplicar</h2>
<p>No Kredor, cada cobrança gera um <a href="/cobranca-pix">PIX dinâmico com baixa automática</a>. Você deixa de conferir extrato e passa a ver o status atualizado em tempo real.</p>
<h2>Conclusão</h2>
<p>PIX dinâmico é padrão para quem cobra em escala. Menos trabalho manual, menos erro e dinheiro reconhecido na hora.</p>
""",
    },
]


async def main():
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'gestorcred')]
    for p in POSTS:
        doc = {
            **p,
            "autor": "Equipe Kredor",
            "publicado": True,
            "data_publicacao": NOW,
            "updated_at": NOW,
        }
        existing = await db.blog_posts.find_one({"slug": p["slug"]})
        if existing:
            doc["data_publicacao"] = existing.get("data_publicacao", NOW)
            await db.blog_posts.update_one({"slug": p["slug"]}, {"$set": doc})
            print("atualizado:", p["slug"])
        else:
            await db.blog_posts.insert_one(doc)
            print("criado:", p["slug"])
    try:
        await db.blog_posts.create_index("slug", unique=True)
    except Exception:
        pass
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
