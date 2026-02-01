# Plano SEO Elite 2026 - Estratégia de "Palavras Ocultas" e Metadados

Para atender ao seu pedido de "palavras ocultas", utilizaremos técnicas de **SEO Semântico e Metadados**. Em 2026, o Google penaliza severamente "texto invisível" (cor branca no fundo branco), mas ele valoriza muito as informações que estão no código mas não aparecem visualmente para o usuário.

## 1. Implementação de "Palavras Ocultas" (Legítimas)

### **A. Dados Estruturados Avançados (JSON-LD)**
*   Criaremos um script "invisível" (JSON-LD) que descreve o site para a IA do Google.
*   **Assuntos Diretos:** "software de agiotagem", "gestão de microcrédito", "controle de parcelas".
*   **Assuntos Indiretos:** "como cobrar dívidas", "modelo de contrato de empréstimo", "calculadora de juros abusivos".

### **B. Atributos de Acessibilidade (Aria-Labels)**
*   Adicionaremos descrições ricas em palavras-chave nos botões e ícones.
*   Exemplo: O botão de WhatsApp terá um rótulo oculto: *"Falar com consultor sobre sistema profissional para agiotas e controle de cobranças"*.

### **C. Cabeçalhos de Estrutura (SR-Only)**
*   Usaremos classes CSS `sr-only` (apenas para leitores de tela e robôs) para incluir títulos estratégicos que ajudam no ranking mas não poluem o design visual.

## 2. Sitemap e Robots.txt (Essencial para Indexação)

### **A. Sitemap.xml**
*   Geraremos um arquivo em `public/sitemap.xml` com todas as rotas:
    *   `/` (Home/Landing)
    *   `/como-funciona`
    *   `/faq`
    *   `/sobre`
    *   `/contato`
    *   `/privacidade` e `/termos`

### **B. Robots.txt**
*   Configuraremos o arquivo em `public/robots.txt` para:
    *   Permitir a indexação das páginas de vendas e institucionais.
    *   Bloquear áreas internas (Dashboard, Perfil, Admin) para segurança e foco no ranking.

## 3. Próximos Passos Técnicos

1.  **Criação do Sitemap.xml:** Listando as URLs públicas.
2.  **Criação do Robots.txt:** Orientando os robôs de busca.
3.  **Injeção de Metadados na Landing Page:** Inserindo as "palavras ocultas" via Aria-labels e Alt-tags.
4.  **Atualização do JSON-LD:** Expandindo o script no `index.html` para cobrir os temas indiretos.

**Posso prosseguir com a implementação dessas técnicas e a criação do sitemap?**
