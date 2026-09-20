"""Seed de 15 artigos longos e profissionais do blog (idempotente por slug).

Cobre termos de intenção de busca que o principal concorrente (SysJuros) NÃO
cobre: régua de cobrança no WhatsApp, consulta de CPF/score, microcrédito, CET,
juros de mora, LGPD para credores, gestão de carteira, etc. Cada artigo faz link
interno para a landing page correspondente (SEO + conversão).

Uso:
    python scripts/seed_blog_2026.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

NOW = datetime.now(timezone.utc).isoformat()

DISCLAIMER = (
    '<p><em>Este conteúdo é informativo e não substitui orientação jurídica ou '
    'financeira. O Kredor é um software de gestão e cobrança: não concede '
    'empréstimos nem realiza operações de crédito.</em></p>'
)

POSTS = [
    {
        "slug": "regua-de-cobranca-o-que-e-e-como-montar",
        "titulo": "Régua de cobrança: o que é e como montar uma que realmente recupera crédito",
        "meta_description": "Aprenda o que é régua de cobrança e como montar uma sequência automática no WhatsApp — antes e depois do vencimento — para reduzir a inadimplência.",
        "resumo": "Uma régua de cobrança envia a mensagem certa, na hora certa, para cada cliente. Veja como montar a sua do zero.",
        "categoria": "Cobrança",
        "keyword": "régua de cobrança",
        "cta_to": "/cobranca-whatsapp",
        "cta_label": "Ver a régua de cobrança no WhatsApp",
        "capa": "/og-cobranca-whatsapp.jpg",
        "lido_min": 8,
        "conteudo_html": """
<p>Se você depende da memória para lembrar quem precisa pagar, mais cedo ou mais tarde uma parcela vai passar batida. A <strong>régua de cobrança</strong> resolve isso: em vez de cobrar no improviso, você define uma sequência de mensagens que o sistema dispara automaticamente para cada cliente, no momento certo.</p>

<h2>O que é uma régua de cobrança</h2>
<p>Régua de cobrança é o roteiro de comunicação que acompanha uma parcela do início ao fim: lembretes antes do vencimento, aviso no dia e cobranças em intervalos definidos após o atraso. Cada etapa tem um objetivo, um tom e um canal — no crédito informal, o canal mais eficiente é o WhatsApp.</p>

<h2>Por que a régua funciona melhor que a cobrança manual</h2>
<ul>
<li><strong>Consistência:</strong> todo cliente recebe o mesmo tratamento, sem esquecimento.</li>
<li><strong>Timing:</strong> a mensagem sai na hora de maior chance de pagamento, não quando você lembra.</li>
<li><strong>Escala:</strong> funciona igual para 10 ou 500 clientes.</li>
<li><strong>Registro:</strong> fica o histórico de tudo que foi enviado, útil em qualquer disputa.</li>
</ul>

<h2>Estrutura de uma régua que converte</h2>
<p>Uma régua eficiente combina prevenção e recuperação. Um modelo testado no mercado:</p>
<ol>
<li><strong>D-3 (três dias antes):</strong> lembrete amigável com o valor, a data e o PIX pronto.</li>
<li><strong>D0 (dia do vencimento):</strong> aviso objetivo de que a parcela vence hoje.</li>
<li><strong>D+1:</strong> primeiro toque de atraso, ainda cordial, oferecendo ajuda.</li>
<li><strong>D+3:</strong> mensagem mais firme, reforçando as consequências do atraso.</li>
<li><strong>D+7:</strong> proposta de regularização (parcial ou renegociação).</li>
</ol>

<h2>Modelos de mensagem por etapa</h2>
<p>Use variáveis para personalizar sem trabalho manual:</p>
<ul>
<li><em>Lembrete (D-3):</em> "Oi, {nome}! Passando para lembrar: sua parcela de {valor} vence em {data}. Já deixo o PIX aqui para facilitar: {link}."</li>
<li><em>Vencimento (D0):</em> "{nome}, hoje é o vencimento da parcela de {valor}. Pode pagar por aqui: {link}. Qualquer dúvida, é só chamar."</li>
<li><em>Atraso (D+3):</em> "{nome}, sua parcela de {valor} venceu em {data} e ainda consta em aberto. Consegue regularizar hoje? PIX: {link}."</li>
</ul>

<h2>Cuidados para não ter o número bloqueado</h2>
<p>WhatsApp penaliza envios em massa que parecem spam. Para preservar seu número: limite a frequência de mensagens, personalize o conteúdo, evite links suspeitos e não dispare tudo de uma vez. Um bom sistema já traz <strong>proteção anti-spam</strong> com controle de cadência.</p>

<h2>Como automatizar na prática</h2>
<p>Montar isso na mão é inviável. No Kredor, você configura a <a href="/cobranca-whatsapp">régua de cobrança no WhatsApp</a> uma vez e ela roda para toda a carteira, já com o <a href="/cobranca-pix">PIX dinâmico</a> embutido e baixa automática quando o cliente paga.</p>

<h2>Conclusão</h2>
<p>Régua de cobrança não é sobre pressionar o cliente: é sobre lembrar na hora certa, facilitar o pagamento e manter o relacionamento. Automatizada, ela recupera crédito enquanto você cuida do resto do negócio.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "consulta-de-cpf-para-analise-de-credito",
        "titulo": "Consulta de CPF para análise de crédito: o que olhar antes de emprestar",
        "meta_description": "Veja como usar a consulta de CPF na análise de crédito: situação cadastral, restrições e score para decidir quanto e a quem emprestar com segurança.",
        "resumo": "Emprestar sem consultar o CPF é apostar no escuro. Entenda o que a consulta mostra e como usar na decisão.",
        "categoria": "Análise de crédito",
        "keyword": "consulta de cpf crédito",
        "cta_to": "/consulta-cpf-credito",
        "cta_label": "Conhecer a consulta de CPF integrada",
        "capa": "/og-gestao-de-clientes.jpg",
        "lido_min": 7,
        "conteudo_html": """
<p>A maior parte do prejuízo de um credor nasce na largada: emprestar para quem já não estava conseguindo pagar. A <strong>consulta de CPF</strong> é a forma mais rápida e barata de reduzir esse risco antes de liberar o dinheiro.</p>

<h2>Por que consultar o CPF antes de emprestar</h2>
<p>A consulta transforma "achismo" em dado. Em segundos você sabe se a pessoa existe, se o CPF está regular e se há sinais de risco. Isso não elimina o calote, mas melhora muito a qualidade da carteira ao longo do tempo.</p>

<h2>O que a consulta costuma mostrar</h2>
<ul>
<li><strong>Situação cadastral do CPF:</strong> regular, pendente, suspenso ou cancelado na Receita.</li>
<li><strong>Dados de identificação:</strong> nome, data de nascimento e vínculos básicos, úteis para confirmar identidade.</li>
<li><strong>Restrições e apontamentos:</strong> indícios de dívidas em aberto e negativações.</li>
<li><strong>Score de crédito:</strong> uma nota que resume a probabilidade de pagamento.</li>
</ul>

<h2>Como interpretar o resultado</h2>
<p>Não existe "aprovado ou reprovado" automático — existe risco a ser precificado. Um CPF com boa situação e score alto permite valores maiores e taxas menores. Um CPF com restrições não significa "nunca empreste", mas sugere <strong>valor menor, prazo mais curto e garantias</strong>.</p>

<h2>Transforme a consulta em política de crédito</h2>
<p>Defina regras claras e aplique a todos os clientes:</p>
<ol>
<li>Faixa de score A: até X reais, taxa padrão.</li>
<li>Faixa B: até metade do valor, com lembrete de garantia.</li>
<li>Faixa C: valor simbólico ou recusa educada.</li>
</ol>
<p>Política escrita evita decisões emocionais e protege seu caixa.</p>

<h2>LGPD: consulte com responsabilidade</h2>
<p>Dados de CPF são dados pessoais. Consulte apenas com finalidade legítima (análise de crédito), informe o cliente e guarde as informações com segurança. Veja mais no nosso guia sobre <a href="/blog/lgpd-para-credores-como-tratar-dados-dos-clientes">LGPD para credores</a>.</p>

<h2>Como fazer isso sem sair do sistema</h2>
<p>No Kredor, a <a href="/consulta-cpf-credito">consulta de CPF é integrada ao cadastro</a>: você analisa o cliente no momento de cadastrar, registra a decisão e mantém tudo organizado na ficha.</p>

<h2>Conclusão</h2>
<p>Consultar o CPF é o passo mais barato para evitar o calote mais caro. Padronize a análise, precifique o risco e empreste com base em dados — não em confiança cega.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "como-montar-operacao-de-microcredito",
        "titulo": "Como montar uma operação de microcrédito do zero (guia prático)",
        "meta_description": "Guia para montar uma operação de microcrédito: definição de público, política de crédito, precificação, cobrança e ferramentas de gestão.",
        "resumo": "Do primeiro empréstimo à carteira organizada: os passos para operar microcrédito com método e segurança.",
        "categoria": "Microcrédito",
        "keyword": "operação de microcrédito",
        "cta_to": "/sistema-microcredito",
        "cta_label": "Ver sistema para microcrédito",
        "capa": "/og-sistema-gestao-emprestimos.jpg",
        "lido_min": 9,
        "conteudo_html": """
<p>Microcrédito é conceder valores pequenos, com prazos curtos e alta rotatividade, geralmente para pessoas fora do sistema bancário tradicional. É um negócio de <strong>volume, disciplina e cobrança</strong> — e não de sorte.</p>

<h2>1. Defina seu público e seu ticket</h2>
<p>Quem você vai atender? Comerciantes de bairro, autônomos, colegas de trabalho? Defina o valor médio (ticket), o prazo típico e a frequência (diária, semanal, quinzenal ou mensal). Isso molda toda a operação.</p>

<h2>2. Crie uma política de crédito</h2>
<p>Antes de emprestar o primeiro real, escreva suas regras: valor máximo por cliente novo, exigência de <a href="/consulta-cpf-credito">consulta de CPF</a>, faixas de score e critérios para aumentar o limite de bons pagadores. Política no papel evita decisão no impulso.</p>

<h2>3. Precifique corretamente</h2>
<p>Sua taxa precisa cobrir três coisas: o custo do dinheiro, o risco de inadimplência e a sua margem. Simule diferentes cenários com uma <a href="/calculadora-de-juros">calculadora de juros</a> e entenda a diferença entre juros simples, compostos, Price e SAC antes de definir o preço.</p>

<h2>4. Formalize cada empréstimo</h2>
<p>Mesmo em valores pequenos, um contrato protege as duas partes. Uma <a href="/contratos-digitais-ccb">CCB digital</a> registra valor, juros, encargos de mora e datas, e facilita a cobrança em caso de atraso.</p>

<h2>5. Monte a máquina de cobrança</h2>
<p>No microcrédito, a cobrança é o coração da operação. Configure uma <a href="/cobranca-whatsapp">régua de cobrança no WhatsApp</a> com lembretes antes do vencimento e avisos após o atraso, sempre com o <a href="/cobranca-pix">PIX pronto</a> na mensagem. Facilitar o pagamento é o que mantém a inadimplência baixa.</p>

<h2>6. Acompanhe os indicadores certos</h2>
<ul>
<li><strong>Inadimplência (%):</strong> saldo vencido sobre o total da carteira.</li>
<li><strong>Capital exposto:</strong> quanto do seu dinheiro está na rua.</li>
<li><strong>Rentabilidade:</strong> recebido menos custo e perdas.</li>
<li><strong>Rotatividade:</strong> quantas vezes o capital gira no mês.</li>
</ul>

<h2>7. Reinvista com disciplina</h2>
<p>A tentação de gastar o que entrou é o maior inimigo do microcrédito. Separe a margem, mantenha uma reserva para perdas e reinvista o principal. É assim que a carteira cresce de forma saudável.</p>

<h2>Erros comuns de quem começa</h2>
<ul>
<li>Emprestar valores altos para clientes novos sem histórico.</li>
<li>Não consultar o CPF "para não perder o cliente".</li>
<li>Misturar o caixa da operação com o dinheiro pessoal.</li>
<li>Cobrar só quando lembra — e tarde demais.</li>
</ul>

<h2>Conclusão</h2>
<p>Microcrédito dá certo com processo: público definido, política clara, preço correto, contrato e cobrança automática. Um <a href="/sistema-microcredito">sistema para microcrédito</a> junta tudo isso em um só lugar e substitui o caderninho por dados confiáveis.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "score-de-credito-como-interpretar",
        "titulo": "Score de crédito: como interpretar e usar para reduzir a inadimplência",
        "meta_description": "Entenda o que é score de crédito, o que influencia a nota e como usar as faixas de score para decidir quanto emprestar e a que taxa.",
        "resumo": "O score resume o risco de calote em uma nota. Veja como ler as faixas e transformá-las em decisão.",
        "categoria": "Análise de crédito",
        "keyword": "score de crédito",
        "cta_to": "/consulta-cpf-credito",
        "cta_label": "Analisar clientes por score",
        "capa": "/og-gestao-de-clientes.jpg",
        "lido_min": 6,
        "conteudo_html": """
<p>O <strong>score de crédito</strong> é uma nota, normalmente de 0 a 1000, que estima a probabilidade de uma pessoa pagar suas contas nos próximos meses. Quanto maior a nota, menor o risco. Para o credor, é um atalho poderoso — desde que bem interpretado.</p>

<h2>O que influencia o score</h2>
<ul>
<li><strong>Histórico de pagamento:</strong> contas pagas em dia elevam a nota; atrasos e negativações derrubam.</li>
<li><strong>Nível de endividamento:</strong> muitas dívidas ativas aumentam o risco.</li>
<li><strong>Idade e estabilidade do cadastro:</strong> dados consistentes ajudam.</li>
<li><strong>Consultas recentes:</strong> muitas consultas em pouco tempo podem indicar busca por crédito em excesso.</li>
</ul>

<h2>Como ler as faixas</h2>
<table>
<thead><tr><th>Faixa</th><th>Risco</th><th>Sugestão de conduta</th></tr></thead>
<tbody>
<tr><td>Alta (700–1000)</td><td>Baixo</td><td>Valores maiores, taxa padrão, aprovação ágil.</td></tr>
<tr><td>Média (500–699)</td><td>Moderado</td><td>Valor moderado, acompanhar de perto, reforçar lembretes.</td></tr>
<tr><td>Baixa (0–499)</td><td>Alto</td><td>Valor pequeno, prazo curto, garantia ou recusa educada.</td></tr>
</tbody>
</table>

<h2>Score não é destino</h2>
<p>Uma nota baixa não significa "nunca empreste"; significa "empreste com mais cuidado". Muitos bons clientes começam com score baixo por falta de histórico. Use o score junto com a <a href="/blog/consulta-de-cpf-para-analise-de-credito">consulta de CPF</a> e o seu conhecimento do cliente.</p>

<h2>Transforme score em política</h2>
<p>Defina limites por faixa e aplique a todos. Assim você elimina a decisão emocional ("mas ele é meu conhecido") e protege o caixa. Com o tempo, promova os bons pagadores para limites maiores — isso fideliza e aumenta a rentabilidade.</p>

<h2>Como usar no dia a dia</h2>
<p>No Kredor, o score aparece na <a href="/consulta-cpf-credito">análise de CPF integrada ao cadastro</a>, então a decisão acontece no mesmo lugar em que você registra o cliente e o empréstimo.</p>

<h2>Conclusão</h2>
<p>O score é uma bússola, não um oráculo. Combine a nota com política clara e cobrança eficiente e você reduz a inadimplência sem deixar bons negócios na mesa.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "taxa-de-juros-maxima-emprestimo-pessoal",
        "titulo": "Qual a taxa de juros máxima que posso cobrar em um empréstimo pessoal?",
        "meta_description": "Entenda os limites de juros para empréstimos entre particulares, o conceito de usura e como definir uma taxa justa e sustentável.",
        "resumo": "Existe limite para os juros? Entenda usura, a diferença para instituições financeiras e como precificar com bom senso.",
        "categoria": "Juros",
        "keyword": "taxa de juros máxima empréstimo",
        "cta_to": "/calculadora-de-juros",
        "cta_label": "Simular juros na calculadora",
        "capa": "/og-controle-de-parcelas-e-juros.jpg",
        "lido_min": 7,
        "conteudo_html": """
<p>Uma das dúvidas mais comuns de quem empresta é: "até quanto de juros eu posso cobrar?". A resposta curta é que <strong>particulares não têm a mesma liberdade das instituições financeiras</strong> — e cobrar demais pode invalidar a cobrança.</p>

<h2>Usura: o limite histórico para particulares</h2>
<p>No Brasil, a chamada Lei da Usura tradicionalmente limita os juros cobrados por quem não é instituição financeira. Historicamente, o teto discutido nos tribunais para pessoas físicas gira em torno de <strong>1% ao mês</strong> (12% ao ano) para juros remuneratórios, salvo situações específicas. Bancos e financeiras, por outro lado, seguem regras próprias e podem cobrar taxas maiores.</p>
<p><strong>Importante:</strong> as regras e a interpretação variam conforme o caso e a jurisprudência. Antes de definir taxas, consulte um advogado — este artigo é apenas informativo.</p>

<h2>Juros remuneratórios x juros de mora</h2>
<ul>
<li><strong>Remuneratórios:</strong> a "remuneração" do empréstimo, combinada na contratação.</li>
<li><strong>Mora:</strong> encargo por atraso, geralmente limitado (comumente até 1% ao mês) somado à multa (em muitos contratos, até 2%).</li>
</ul>

<h2>Por que cobrar demais é um mau negócio</h2>
<ol>
<li><strong>Risco jurídico:</strong> taxas abusivas podem ser reduzidas judicialmente, e você recebe menos do que esperava.</li>
<li><strong>Inadimplência:</strong> parcela alta demais aumenta o calote — melhor receber um pouco menos e receber de fato.</li>
<li><strong>Reputação:</strong> no crédito informal, indicação boca a boca vale ouro.</li>
</ol>

<h2>Como definir uma taxa sustentável</h2>
<p>Precifique cobrindo custo do dinheiro, risco (medido por <a href="/blog/score-de-credito-como-interpretar">score</a>) e margem. Simule diferentes taxas e prazos na <a href="/calculadora-de-juros">calculadora de juros</a> e escolha um valor que o cliente consiga pagar com folga.</p>

<h2>Formalize sempre</h2>
<p>Uma taxa bem definida só protege você se estiver escrita. Registre juros, mora e multa em uma <a href="/contratos-digitais-ccb">CCB</a> clara.</p>

<h2>Conclusão</h2>
<p>Mais importante que cobrar o máximo é cobrar o sustentável e receber. Precifique com bom senso, formalize e deixe a cobrança no automático.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "cet-custo-efetivo-total-como-calcular",
        "titulo": "CET (Custo Efetivo Total): o que é e como calcular no seu empréstimo",
        "meta_description": "Entenda o que é o CET (Custo Efetivo Total), por que ele é diferente da taxa de juros e como calcular para dar transparência ao cliente.",
        "resumo": "O CET mostra o custo real do empréstimo além da taxa de juros. Veja o que entra na conta e como calcular.",
        "categoria": "Juros",
        "keyword": "custo efetivo total cet",
        "cta_to": "/calculadora-de-juros",
        "cta_label": "Simular parcelas e juros",
        "capa": "/og-controle-de-parcelas-e-juros.jpg",
        "lido_min": 7,
        "conteudo_html": """
<p>Dois empréstimos podem ter a mesma taxa de juros e custar valores bem diferentes. O que revela o custo real é o <strong>CET — Custo Efetivo Total</strong>, que reúne juros e todos os encargos em uma única taxa.</p>

<h2>O que é o CET</h2>
<p>O CET é a taxa que expressa, em porcentagem ao mês ou ao ano, tudo o que o cliente paga além do valor emprestado: juros, tarifas, seguros e tributos como o IOF. Ele responde à pergunta que importa: "no fim das contas, quanto esse dinheiro me custa?".</p>

<h2>O que entra no CET</h2>
<ul>
<li><strong>Juros remuneratórios</strong> do empréstimo.</li>
<li><strong>Tarifas</strong> (cadastro, emissão, administração).</li>
<li><strong>Tributos</strong> aplicáveis, como o IOF.</li>
<li><strong>Seguros</strong> ou serviços atrelados, quando houver.</li>
</ul>

<h2>CET x taxa de juros</h2>
<p>A taxa de juros é só uma parte. Se você cobra 5% ao mês mas adiciona uma tarifa de cadastro, o CET fica acima de 5%. Por isso duas ofertas com a mesma taxa "nominal" podem ter custos reais distintos.</p>

<h2>Como calcular na prática</h2>
<p>O cálculo exato do CET usa a mesma lógica da taxa interna de retorno (TIR): é a taxa que iguala o valor liberado ao fluxo de pagamentos, já com todos os encargos embutidos. Na prática:</p>
<ol>
<li>Monte o fluxo: valor líquido recebido pelo cliente hoje e cada parcela nas datas futuras.</li>
<li>Some todos os encargos às parcelas (tarifas, IOF, seguros).</li>
<li>Encontre a taxa que "zera" esse fluxo — esse é o CET.</li>
</ol>
<p>Para simular o efeito dos juros e do prazo na parcela, use a <a href="/calculadora-de-juros">calculadora de juros do Kredor</a> e depois some os encargos fixos.</p>

<h2>Por que informar o CET ao cliente</h2>
<p>Transparência gera confiança e reduz disputas. Um cliente que entende o custo total tem menos motivo para questionar a dívida depois. Além disso, mostrar o CET diferencia você de quem esconde tarifas.</p>

<h2>Conclusão</h2>
<p>Taxa de juros é o preço aparente; CET é o preço real. Calcule, informe e formalize — seus números ficam à prova de contestação.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "fluxo-de-caixa-para-credores",
        "titulo": "Fluxo de caixa para credores: como projetar recebimentos e não ficar sem capital",
        "meta_description": "Aprenda a montar o fluxo de caixa de uma carteira de crédito: projeção de recebimentos, reserva para inadimplência e reinvestimento saudável.",
        "resumo": "Saber quanto entra e quando entra é o que impede um credor de ficar sem capital. Veja como projetar.",
        "categoria": "Gestão",
        "keyword": "fluxo de caixa credor",
        "cta_to": "/gestao-carteira-credito",
        "cta_label": "Ver gestão de carteira de crédito",
        "capa": "/og-sistema-gestao-emprestimos.jpg",
        "lido_min": 8,
        "conteudo_html": """
<p>Muitos credores quebram não por falta de lucro, mas por falta de <strong>caixa no momento certo</strong>. Emprestaram tudo, o dinheiro voltaria só daqui a semanas e apareceu uma oportunidade — ou uma emergência. O fluxo de caixa evita esse aperto.</p>

<h2>O que é fluxo de caixa na prática</h2>
<p>É a projeção, dia a dia ou semana a semana, de <strong>quanto entra</strong> (parcelas a receber) e <strong>quanto sai</strong> (novos empréstimos, custos, retiradas). O objetivo é nunca ser surpreendido por um saldo negativo.</p>

<h2>Passo 1: mapeie os recebimentos futuros</h2>
<p>Liste todas as parcelas em aberto com data e valor. Uma boa gestão mostra isso automaticamente em um painel de vencimentos, separando o que vence hoje, esta semana e este mês.</p>

<h2>Passo 2: aplique um fator de inadimplência</h2>
<p>Nem tudo que está previsto entra. Se sua inadimplência histórica é de 10%, projete recebendo 90% do previsto. É melhor ser conservador e ter caixa sobrando do que otimista e ficar no vermelho.</p>

<h2>Passo 3: planeje as saídas</h2>
<p>Some novos empréstimos planejados, custos operacionais e sua retirada mensal. Confronte com os recebimentos projetados semana a semana.</p>

<h2>Passo 4: mantenha uma reserva</h2>
<p>Guarde uma parte do que entra como colchão para atrasos e imprevistos. Uma reserva equivalente a algumas semanas de operação dá tranquilidade para não recusar bons negócios.</p>

<h2>Indicadores que sustentam o fluxo</h2>
<ul>
<li><strong>Capital exposto:</strong> quanto do seu dinheiro está na rua agora.</li>
<li><strong>Recebimentos previstos por período.</strong></li>
<li><strong>Taxa de inadimplência</strong> para ajustar a projeção.</li>
<li><strong>Prazo médio de retorno</strong> do capital.</li>
</ul>

<h2>Automatize a projeção</h2>
<p>Fazer isso em planilha é trabalhoso e envelhece rápido. Na <a href="/gestao-carteira-credito">gestão de carteira do Kredor</a>, os recebimentos futuros e os indicadores são calculados a partir das parcelas reais, então o fluxo se atualiza sozinho a cada pagamento.</p>

<h2>Conclusão</h2>
<p>Lucro é opinião; caixa é fato. Projete recebimentos com margem de segurança, mantenha reserva e reinvista com disciplina — assim a carteira cresce sem sustos.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "como-reduzir-inadimplencia-carteira-de-credito",
        "titulo": "Como reduzir a inadimplência na sua carteira de crédito (10 ações práticas)",
        "meta_description": "10 ações práticas para reduzir a inadimplência: análise na entrada, precificação por risco, cobrança automática, facilitação do pagamento e renegociação.",
        "resumo": "Inadimplência se combate na entrada e na cobrança. Veja 10 ações que reduzem o calote de forma consistente.",
        "categoria": "Cobrança",
        "keyword": "reduzir inadimplência",
        "cta_to": "/cobranca-whatsapp",
        "cta_label": "Automatizar a cobrança",
        "capa": "/og-cobranca-whatsapp.jpg",
        "lido_min": 8,
        "conteudo_html": """
<p>Inadimplência não é azar: é resultado de processo. Quem controla a entrada e mantém uma cobrança disciplinada recebe muito mais do que quem confia na sorte. Veja 10 ações que funcionam.</p>

<h2>Na concessão (antes de emprestar)</h2>
<ol>
<li><strong>Consulte o CPF sempre.</strong> A <a href="/consulta-cpf-credito">análise de CPF</a> filtra o risco mais óbvio na largada.</li>
<li><strong>Precifique por risco.</strong> Use faixas de <a href="/blog/score-de-credito-como-interpretar">score</a> para definir valor e taxa.</li>
<li><strong>Comece pequeno com clientes novos.</strong> Aumente o limite conforme o histórico de pagamento.</li>
<li><strong>Formalize com contrato.</strong> Uma <a href="/contratos-digitais-ccb">CCB</a> dá respaldo e reduz "esquecimentos" convenientes.</li>
</ol>

<h2>Na cobrança (durante o empréstimo)</h2>
<ol start="5">
<li><strong>Lembre antes do vencimento.</strong> Boa parte do atraso é esquecimento; um lembrete resolve.</li>
<li><strong>Facilite o pagamento.</strong> Envie o <a href="/cobranca-pix">PIX pronto</a> na mensagem — quanto mais fácil, mais rápido o cliente paga.</li>
<li><strong>Use uma régua automática.</strong> A <a href="/cobranca-whatsapp">régua no WhatsApp</a> garante consistência e escala.</li>
<li><strong>Mantenha o tom profissional.</strong> Respeito preserva o relacionamento e a chance de receber.</li>
</ol>

<h2>Na recuperação (depois do atraso)</h2>
<ol start="9">
<li><strong>Ofereça renegociação cedo.</strong> Melhor um acordo hoje do que uma dívida parada por meses.</li>
<li><strong>Acompanhe indicadores.</strong> Meça inadimplência, capital exposto e prazo médio para agir a tempo.</li>
</ol>

<h2>O erro que anula tudo</h2>
<p>Cobrar só quando lembra. Sem cadência, a dívida esfria, o cliente se acostuma com o atraso e a recuperação despenca. A automação existe justamente para eliminar esse ponto fraco.</p>

<h2>Conclusão</h2>
<p>Reduzir inadimplência é somar pequenas disciplinas: análise na entrada, preço por risco, contrato, lembrete, PIX fácil e régua automática. Cada uma tira alguns pontos percentuais do calote — juntas, transformam a carteira.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "como-renegociar-divida-de-cliente",
        "titulo": "Como renegociar dívida de cliente sem perder dinheiro (nem o cliente)",
        "meta_description": "Aprenda a renegociar dívida de cliente inadimplente: quando propor acordo, como recalcular parcelas e formalizar sem prejuízo.",
        "resumo": "Renegociar bem é recuperar o que estava parado. Veja quando e como propor um acordo que fecha.",
        "categoria": "Cobrança",
        "keyword": "renegociar dívida cliente",
        "cta_to": "/sistema-gestao-emprestimos",
        "cta_label": "Ver o sistema de gestão",
        "capa": "/og-sistema-gestao-emprestimos.jpg",
        "lido_min": 7,
        "conteudo_html": """
<p>Uma dívida parada não rende nada. Muitas vezes, um <strong>acordo bem feito</strong> vale mais do que insistir na cobrança integral de quem não tem como pagar. Renegociar é estratégia, não fraqueza.</p>

<h2>Quando propor a renegociação</h2>
<p>Não espere a dívida virar poeira. Depois de alguns avisos sem retorno (por exemplo, a partir de D+7 ou D+15), abra a porta para o acordo. Quanto mais fresca a dívida, maior a chance de fechar.</p>

<h2>Prepare a proposta antes de conversar</h2>
<ul>
<li><strong>Saiba o número exato:</strong> saldo devedor com juros e mora atualizados.</li>
<li><strong>Defina seu piso:</strong> o mínimo que você aceita receber.</li>
<li><strong>Tenha opções:</strong> desconto para pagamento à vista, ou reparcelamento em valores menores.</li>
</ul>

<h2>Estruturas de acordo que funcionam</h2>
<ol>
<li><strong>Desconto à vista:</strong> abre mão de parte dos encargos em troca do pagamento imediato. Ótimo para o caixa.</li>
<li><strong>Reparcelamento:</strong> divide o saldo em parcelas que cabem no bolso do cliente, com novas datas.</li>
<li><strong>Entrada + saldo:</strong> um valor de entrada demonstra compromisso e reduz o risco do acordo furar.</li>
</ol>

<h2>Conduza a conversa com respeito</h2>
<p>Ouça o motivo do atraso, mostre que quer resolver e apresente a saída. Cliente encurralado não paga; cliente com uma saída digna, sim. O objetivo é um "sim" que ele consiga cumprir.</p>

<h2>Formalize o novo acordo</h2>
<p>Todo acordo precisa virar registro: novas parcelas, novas datas e assinatura. Sem formalização, você troca uma dívida por outra igualmente frágil. Um <a href="/sistema-gestao-emprestimos">sistema de gestão</a> permite reparcelar e gerar o novo cronograma na hora, já com <a href="/cobranca-pix">PIX</a> por parcela.</p>

<h2>Depois do acordo, reative a régua</h2>
<p>Volte a enviar lembretes automáticos para as novas parcelas. O acordo só é bom se for cumprido — e a <a href="/cobranca-whatsapp">cobrança automática</a> ajuda a manter o cliente em dia.</p>

<h2>Conclusão</h2>
<p>Renegociar é transformar dívida parada em dinheiro no caixa. Proponha cedo, ofereça uma saída viável, formalize e acompanhe. Todo mundo sai ganhando.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "indicadores-para-gestao-de-carteira-de-credito",
        "titulo": "Indicadores essenciais para a gestão de uma carteira de crédito",
        "meta_description": "Conheça os indicadores que todo credor deve acompanhar: inadimplência, capital exposto, rentabilidade, prazo médio e ticket médio.",
        "resumo": "Sem números, você opera no escuro. Veja os indicadores que mostram a saúde real da sua carteira.",
        "categoria": "Gestão",
        "keyword": "gestão de carteira de crédito",
        "cta_to": "/gestao-carteira-credito",
        "cta_label": "Ver gestão de carteira",
        "capa": "/og-sistema-gestao-emprestimos.jpg",
        "lido_min": 7,
        "conteudo_html": """
<p>Gerir uma carteira de crédito no "feeling" funciona até certo ponto. Para crescer com segurança, você precisa de <strong>indicadores</strong> — números que mostram a saúde da operação e apontam onde agir.</p>

<h2>1. Taxa de inadimplência</h2>
<p>Saldo vencido dividido pelo total da carteira. É o termômetro principal. Acompanhe a tendência: subir dois meses seguidos é sinal de alerta na concessão ou na cobrança.</p>

<h2>2. Capital exposto</h2>
<p>Quanto do seu dinheiro está "na rua" neste momento. Ajuda a dosar novos empréstimos e a não ficar sem caixa.</p>

<h2>3. Rentabilidade</h2>
<p>Recebido menos custo do dinheiro e menos perdas. Lucro bruto não é lucro real — desconte a inadimplência para saber o que sobra de fato.</p>

<h2>4. Prazo médio de recebimento</h2>
<p>Quanto tempo, em média, seu capital leva para voltar. Prazos mais curtos giram mais o dinheiro e aumentam o retorno anual.</p>

<h2>5. Ticket médio</h2>
<p>Valor médio emprestado por contrato. Crescer o ticket sem piorar a inadimplência é sinal de carteira madura.</p>

<h2>6. Taxa de recuperação</h2>
<p>Dos valores que atrasaram, quanto você conseguiu receber. Mede a eficiência da sua <a href="/cobranca-whatsapp">cobrança</a>.</p>

<h2>Como usar os indicadores</h2>
<ol>
<li>Olhe a tendência, não só o número do dia.</li>
<li>Cruze indicadores: inadimplência subindo + ticket subindo = revisar concessão.</li>
<li>Defina metas e revise mensalmente.</li>
</ol>

<h2>Painel em vez de planilha</h2>
<p>Recalcular tudo na mão é lento e sujeito a erro. Na <a href="/gestao-carteira-credito">gestão de carteira do Kredor</a>, esses indicadores saem prontos a partir das parcelas reais, atualizados a cada pagamento.</p>

<h2>Conclusão</h2>
<p>O que não se mede não se melhora. Acompanhe inadimplência, capital exposto, rentabilidade e prazo médio e tome decisões com base em dados — não em impressões.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "lgpd-para-credores-como-tratar-dados-dos-clientes",
        "titulo": "LGPD para credores: como tratar os dados dos clientes com segurança",
        "meta_description": "Guia de LGPD para credores: base legal para consultar CPF, princípios de tratamento de dados, segurança e direitos do titular.",
        "resumo": "Quem empresta lida com dados sensíveis. Veja como cumprir a LGPD e proteger clientes e operação.",
        "categoria": "Segurança",
        "keyword": "lgpd credores",
        "cta_to": "/consulta-cpf-credito",
        "cta_label": "Consulta de CPF em conformidade",
        "capa": "/og-image-kredor.jpg",
        "lido_min": 7,
        "conteudo_html": """
<p>Quem concede crédito coleta CPF, telefone, endereço e histórico financeiro — todos <strong>dados pessoais</strong> protegidos pela LGPD (Lei Geral de Proteção de Dados). Tratar isso corretamente não é só obrigação legal: é confiança e reputação.</p>

<h2>A LGPD se aplica a mim?</h2>
<p>Sim. A LGPD vale para qualquer pessoa física ou jurídica que trate dados pessoais em atividade econômica — inclusive credores informais e microcrédito. O tamanho da operação não isenta.</p>

<h2>Base legal para consultar e usar os dados</h2>
<p>Para <a href="/consulta-cpf-credito">consultar o CPF</a> e analisar crédito, a base legal costuma ser a <strong>execução de contrato</strong> e o <strong>legítimo interesse</strong> (avaliar risco antes de emprestar). Use os dados apenas para essa finalidade — nada de repassar ou usar para outra coisa.</p>

<h2>Princípios que você deve seguir</h2>
<ul>
<li><strong>Finalidade:</strong> colete só o necessário para a operação de crédito.</li>
<li><strong>Transparência:</strong> informe o cliente sobre quais dados você guarda e por quê.</li>
<li><strong>Segurança:</strong> proteja os dados contra vazamento e acesso indevido.</li>
<li><strong>Necessidade:</strong> não guarde dados por mais tempo do que precisa.</li>
</ul>

<h2>Direitos do cliente (titular)</h2>
<p>O cliente pode pedir acesso aos próprios dados, correção de informações erradas e, em certos casos, exclusão. Tenha um canal simples para atender esses pedidos.</p>

<h2>Segurança na prática</h2>
<ol>
<li>Use senhas fortes e não compartilhe acessos.</li>
<li>Prefira sistemas com <strong>criptografia</strong> e backup, em vez de planilhas soltas no computador.</li>
<li>Restrinja quem, na sua operação, vê dados sensíveis.</li>
<li>Evite trafegar dados por grupos de mensagem abertos.</li>
</ol>

<h2>Por que um sistema ajuda na conformidade</h2>
<p>Guardar tudo em planilha ou papel é o oposto de LGPD. Um sistema com controle de acesso, criptografia e registro de atividades reduz drasticamente o risco — e o Kredor foi construído com esses cuidados.</p>

<h2>Conclusão</h2>
<p>Respeitar a LGPD é proteger o cliente e a si mesmo. Colete o necessário, seja transparente, guarde com segurança e use ferramentas feitas para isso.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "juros-de-mora-e-multa-por-atraso",
        "titulo": "Juros de mora e multa por atraso: como calcular corretamente",
        "meta_description": "Entenda a diferença entre juros de mora e multa por atraso, os limites usuais e como aplicar os encargos de forma correta e automática.",
        "resumo": "Atrasou, incidem encargos — mas quais e quanto? Entenda mora, multa e como calcular sem exagero.",
        "categoria": "Juros",
        "keyword": "juros de mora e multa",
        "cta_to": "/controle-de-parcelas-e-juros",
        "cta_label": "Ver controle de parcelas e juros",
        "capa": "/og-controle-de-parcelas-e-juros.jpg",
        "lido_min": 6,
        "conteudo_html": """
<p>Quando uma parcela atrasa, é justo aplicar encargos — mas eles precisam ser corretos e previstos em contrato. Confundir <strong>juros de mora</strong> com <strong>multa</strong> é um erro comum que gera contestação.</p>

<h2>Multa por atraso: valor fixo, uma vez</h2>
<p>A multa é um percentual aplicado <strong>uma única vez</strong> sobre o valor em atraso, no momento em que o atraso ocorre. Em contratos de consumo, costuma ser limitada a <strong>2%</strong>. Exemplo: parcela de R$ 500 com multa de 2% = R$ 10,00.</p>

<h2>Juros de mora: acumulam por dia/mês de atraso</h2>
<p>Os juros de mora "correm" enquanto a dívida não é paga, proporcional ao tempo de atraso. Um patamar comum é <strong>1% ao mês</strong> (cerca de 0,0333% ao dia). Exemplo: R$ 500 em atraso, 1% ao mês, 15 dias ≈ R$ 2,50.</p>

<h2>Colocando tudo junto</h2>
<table>
<thead><tr><th>Item</th><th>Cálculo</th><th>Valor</th></tr></thead>
<tbody>
<tr><td>Parcela original</td><td>—</td><td>R$ 500,00</td></tr>
<tr><td>Multa (2%)</td><td>500 × 2%</td><td>R$ 10,00</td></tr>
<tr><td>Mora (1% a.m., 15 dias)</td><td>500 × 1% × 15/30</td><td>R$ 2,50</td></tr>
<tr><td><strong>Total a pagar</strong></td><td>—</td><td><strong>R$ 512,50</strong></td></tr>
</tbody>
</table>

<h2>Cuidados importantes</h2>
<ul>
<li><strong>Sempre em contrato:</strong> encargos só valem se estiverem previstos e claros.</li>
<li><strong>Sem cumular indevidamente:</strong> multa é uma vez; mora é pelo tempo. Não some duas multas.</li>
<li><strong>Bom senso:</strong> encargos excessivos podem ser reduzidos judicialmente.</li>
</ul>

<h2>Automatize para não errar</h2>
<p>Calcular mora dia a dia na mão é trabalhoso e propenso a erro. No <a href="/controle-de-parcelas-e-juros">controle de parcelas e juros do Kredor</a>, você define multa e mora uma vez e o sistema atualiza o valor devido automaticamente conforme o atraso.</p>

<h2>Conclusão</h2>
<p>Encargo correto é aquele previsto em contrato, calculado certo e aplicado com bom senso. Deixe o cálculo com o sistema e cobre com segurança.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "emprestimo-entre-pessoas-fisicas-regras-e-boas-praticas",
        "titulo": "Empréstimo entre pessoas físicas: regras e boas práticas",
        "meta_description": "Saiba como funciona o empréstimo entre pessoas físicas: contrato, juros permitidos, garantias, riscos e como se proteger.",
        "resumo": "Emprestar para conhecidos é comum — e arriscado sem cuidado. Veja as regras e boas práticas para se proteger.",
        "categoria": "Contratos",
        "keyword": "empréstimo entre pessoas físicas",
        "cta_to": "/contratos-digitais-ccb",
        "cta_label": "Gerar contrato de empréstimo",
        "capa": "/og-image-kredor.jpg",
        "lido_min": 7,
        "conteudo_html": """
<p>Emprestar dinheiro para outra pessoa física é permitido e muito comum. O problema não é a operação em si, mas fazê-la <strong>sem formalização</strong> — é aí que amizade vira dívida e dívida vira briga.</p>

<h2>É legal emprestar como pessoa física?</h2>
<p>Sim, desde que não seja atividade financeira habitual e organizada como se fosse um banco. Empréstimos ocasionais entre particulares são lícitos, mas seguem limites de juros mais restritos do que os de instituições financeiras (veja nosso texto sobre <a href="/blog/taxa-de-juros-maxima-emprestimo-pessoal">taxa máxima de juros</a>).</p>

<h2>Sempre faça contrato</h2>
<p>Mesmo entre conhecidos, registre por escrito. Um contrato — idealmente uma <a href="/contratos-digitais-ccb">CCB</a> — deve conter:</p>
<ul>
<li>Identificação completa das partes (nome, CPF, endereço).</li>
<li>Valor emprestado e finalidade.</li>
<li>Taxa de juros, multa e juros de mora.</li>
<li>Prazo, número de parcelas e datas de vencimento.</li>
<li>Forma de pagamento (ex.: PIX) e assinaturas.</li>
</ul>

<h2>Garantias reduzem o risco</h2>
<p>Para valores maiores, considere garantias: avalista, nota promissória ou bem em garantia. Elas aumentam a chance de recuperação em caso de calote.</p>

<h2>Boas práticas que evitam dor de cabeça</h2>
<ol>
<li><strong>Transfira por PIX/TED</strong>, nunca só em dinheiro — o comprovante prova o empréstimo.</li>
<li><strong>Combine tudo por escrito</strong> antes de liberar o valor.</li>
<li><strong>Emita recibo</strong> a cada pagamento recebido.</li>
<li><strong>Não misture</strong> o dinheiro do empréstimo com contas pessoais.</li>
</ol>

<h2>E se o cliente não pagar?</h2>
<p>Com contrato e comprovantes, você tem base para cobrar extrajudicialmente e, se necessário, judicialmente. A CCB, em especial, é um título executivo — o que agiliza a cobrança.</p>

<h2>Conclusão</h2>
<p>Empréstimo entre pessoas físicas é seguro quando é formal: contrato claro, transferência rastreável, juros dentro do limite e recibos. Formalizar custa pouco e evita perder dinheiro e relacionamento.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "price-ou-sac-qual-escolher-para-emprestimos",
        "titulo": "Price ou SAC: qual escolher para empréstimos particulares?",
        "meta_description": "Comparação entre Tabela Price e SAC: como cada sistema calcula as parcelas, qual gera menos juros e quando usar cada um.",
        "resumo": "Parcela fixa ou decrescente? Entenda as diferenças entre Price e SAC e escolha o melhor para cada operação.",
        "categoria": "Juros",
        "keyword": "price ou sac",
        "cta_to": "/calculadora-de-juros",
        "cta_label": "Comparar Price e SAC na calculadora",
        "capa": "/og-controle-de-parcelas-e-juros.jpg",
        "lido_min": 7,
        "conteudo_html": """
<p>Ao parcelar um empréstimo, dois sistemas dominam: a <strong>Tabela Price</strong> (parcela fixa) e o <strong>SAC</strong> (parcela decrescente). Escolher entre eles muda o valor das parcelas e o total de juros pago.</p>

<h2>Como funciona a Tabela Price</h2>
<p>Na Price, todas as parcelas têm o <strong>mesmo valor</strong> do início ao fim. No começo, a parcela é composta por mais juros e menos amortização; com o tempo, a proporção se inverte. É a mais previsível para o cliente.</p>

<h2>Como funciona o SAC</h2>
<p>No SAC, a <strong>amortização é constante</strong> (o principal é dividido igualmente entre as parcelas) e os juros incidem sobre o saldo devedor, que cai a cada mês. Resultado: parcelas começam mais altas e vão diminuindo.</p>

<h2>Comparação prática (R$ 1.000, 5% a.m., 6 meses)</h2>
<table>
<thead><tr><th>Sistema</th><th>1ª parcela</th><th>Última parcela</th><th>Total de juros</th></tr></thead>
<tbody>
<tr><td>Tabela Price</td><td>R$ 197,02</td><td>R$ 197,02</td><td>≈ R$ 182,11</td></tr>
<tr><td>SAC</td><td>R$ 216,67</td><td>R$ 175,00</td><td>≈ R$ 175,00</td></tr>
</tbody>
</table>
<p>Repare: o SAC costuma gerar <strong>menos juros no total</strong>, porque você amortiza o principal mais rápido. Em compensação, exige mais do cliente no início.</p>

<h2>Quando usar cada um</h2>
<ul>
<li><strong>Price:</strong> quando o cliente prefere previsibilidade e parcela que cabe no orçamento fixo.</li>
<li><strong>SAC:</strong> quando o cliente aguenta parcelas iniciais maiores e você quer reduzir o custo total dos juros.</li>
</ul>

<h2>Simule antes de decidir</h2>
<p>A melhor forma de escolher é ver os números lado a lado. Use a <a href="/calculadora-de-juros">calculadora de juros do Kredor</a>, alterne entre Price e SAC e compare parcela e total de juros para o seu caso.</p>

<h2>Conclusão</h2>
<p>Não existe "melhor" universal: existe o que faz sentido para o fluxo do cliente e para a sua rentabilidade. Simule, explique a diferença e formalize a escolha no contrato.</p>
""" + DISCLAIMER,
    },
    {
        "slug": "como-organizar-emprestimo-particular-passo-a-passo",
        "titulo": "Como organizar empréstimo particular passo a passo (do caderninho ao sistema)",
        "meta_description": "Passo a passo para organizar empréstimos particulares: cadastro de clientes, cálculo de parcelas, contrato, cobrança automática e controle de recebimentos.",
        "resumo": "Saia do caderninho e organize seus empréstimos particulares com método. Veja o passo a passo completo.",
        "categoria": "Gestão",
        "keyword": "organizar empréstimo particular",
        "cta_to": "/emprestimo-particular-como-organizar",
        "cta_label": "Ver como organizar empréstimos",
        "capa": "/og-sistema-gestao-emprestimos.jpg",
        "lido_min": 8,
        "conteudo_html": """
<p>Emprestar dinheiro particular funciona bem enquanto são poucos clientes. Quando a carteira cresce, o caderninho e a memória falham — e o prejuízo aparece. Veja como organizar tudo, passo a passo.</p>

<h2>Passo 1: centralize o cadastro dos clientes</h2>
<p>Reúna nome, CPF, telefone e endereço de cada cliente em um só lugar. Aproveite para <a href="/consulta-cpf-credito">consultar o CPF</a> e registrar o risco de cada um. Ficha organizada é a base de tudo.</p>

<h2>Passo 2: registre cada empréstimo com clareza</h2>
<p>Anote valor, taxa, prazo e método de cálculo. Em vez de calcular parcela na mão, use um sistema que gera o cronograma automaticamente — assim você não erra conta nem esquece vencimentos.</p>

<h2>Passo 3: escolha o método de juros</h2>
<p>Decida entre juros simples, compostos, <a href="/blog/price-ou-sac-qual-escolher-para-emprestimos">Price ou SAC</a> conforme o perfil do cliente. Simule na <a href="/calculadora-de-juros">calculadora</a> antes de fechar.</p>

<h2>Passo 4: formalize com contrato</h2>
<p>Gere uma <a href="/contratos-digitais-ccb">CCB digital</a> com valor, juros, mora e datas. Formalizar protege você e dá seriedade à operação.</p>

<h2>Passo 5: automatize a cobrança</h2>
<p>Configure uma <a href="/cobranca-whatsapp">régua no WhatsApp</a> com lembretes antes do vencimento e avisos de atraso, sempre com o <a href="/cobranca-pix">PIX pronto</a>. A baixa acontece sozinha quando o cliente paga.</p>

<h2>Passo 6: controle os recebimentos</h2>
<p>Acompanhe um painel com o que vence hoje, o que está atrasado e o que já foi recebido. Isso substitui a conferência manual e mostra a saúde da carteira em tempo real.</p>

<h2>Passo 7: acompanhe os números</h2>
<p>Meça inadimplência, capital exposto e rentabilidade. Com <a href="/blog/indicadores-para-gestao-de-carteira-de-credito">indicadores</a>, você decide com base em dados e cresce com segurança.</p>

<h2>Do caderninho ao sistema</h2>
<p>Todos esses passos cabem em um único lugar. O Kredor foi feito para <a href="/emprestimo-particular-como-organizar">organizar empréstimos particulares</a> sem planilha: cadastro, cálculo, contrato, cobrança e relatórios integrados.</p>

<h2>Conclusão</h2>
<p>Organização é o que separa o amador do profissional. Centralize, formalize, automatize a cobrança e acompanhe os números — o dinheiro para de escorrer e a carteira cresce com previsibilidade.</p>
""" + DISCLAIMER,
    },
]


async def main():
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'gestorcred')]
    criados = 0
    atualizados = 0
    for p in POSTS:
        doc = {
            **p,
            "autor": "Equipe Kredor",
            "publicado": True,
            "data_publicacao": NOW,
            "updated_at": NOW,
        }
        # Cada artigo usa sua capa OG própria (gerada por scripts/gen_og.py).
        doc["capa"] = f"/og-blog-{p['slug']}.jpg"
        # Tempo de leitura calculado a partir do texto real (~200 palavras/min),
        # para não exibir um valor inflado fixo no seed.
        import math
        import re as _re
        _txt = _re.sub(r"<[^>]+>", " ", p.get("conteudo_html", "") or "")
        doc["lido_min"] = max(1, math.ceil(len(_txt.split()) / 200))
        existing = await db.blog_posts.find_one({"slug": p["slug"]})
        if existing:
            doc["data_publicacao"] = existing.get("data_publicacao", NOW)
            await db.blog_posts.update_one({"slug": p["slug"]}, {"$set": doc})
            atualizados += 1
            print("atualizado:", p["slug"])
        else:
            await db.blog_posts.insert_one(doc)
            criados += 1
            print("criado:", p["slug"])
    try:
        await db.blog_posts.create_index("slug", unique=True)
    except Exception:
        pass
    total = await db.blog_posts.count_documents({"publicado": True})
    print(f"\nResumo: {criados} criados, {atualizados} atualizados. Total publicados: {total}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
