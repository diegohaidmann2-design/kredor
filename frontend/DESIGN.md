# DESIGN.md — Kredor / GestorCred

Regras de design do frontend. Objetivo: interface neutra e profissional, onde a
**cor só aparece quando carrega informação** que o usuário precisa notar.

## Tokens (fonte da verdade)
Definidos em `src/index.css` (:root e tema claro) e mapeados em `tailwind.config.js`.

| Token | Valor (HSL) | Significado ÚNICO |
|---|---|---|
| `--primary` | `160 84% 39%` (verde esmeralda) | Marca, ação primária, estado ativo, destaque positivo |
| `--success` | `160 84% 39%` | Sucesso / valor recebido |
| `--warning` | `38 92% 50%` (âmbar) | Pendente / atenção (ex.: a receber, sandbox) |
| `--destructive` | `0 72% 51%` (vermelho) | Erro / atraso / ação destrutiva |
| `--muted` / `--muted-foreground` | cinza | Neutro, texto secundário, superfícies calmas |
| `--ring` | `160 84% 39%` | Anel de foco de TODOS os inputs |
| `--radius` | `0.75rem` | Raio base (cards = `rounded-lg`, inputs/botões = `rounded-md`) |

## Regras
1. **Marca é verde.** Nunca usar `blue-500/600/700` do Tailwind como cor de ação/marca.
   - Foco de input: sempre `focus:ring-ring` (nunca `focus:ring-blue-500`).
   - Estado ativo (abas, seleção): `bg-primary/10 text-primary border-primary`.
2. **Cor com significado único.** Verde=positivo/ação, âmbar=pendente/atenção,
   vermelho=erro/atraso, cinza=neutro. Não usar uma paleta decorativa diferente
   por categoria (ex.: uma cor por aba). 
3. **Cor de marca de terceiros pode ficar** onde identifica o provedor:
   Asaas (verde), SyncPay (ciano), Outlook (azul), WhatsApp (verde). Só nesses blocos.
4. **Selos (badges):** só quando têm significado para o usuário.
   - Permitido: `PRO` (recurso do plano pago), `SANDBOX/PRODUÇÃO`, `ATUAL`.
   - Proibido: `POPULAR`, `MAIS USADO`, `NOVO` decorativos.
5. **Tipografia:** corpo em `Plus Jakarta Sans`, títulos em `Space Grotesk`
   (`font-display`). Evitar texto <12px em conteúdo; micro-labels no mínimo 11px.
6. **Números:** sempre formatar em pt-BR com separador de milhar
   (`utils/formatters.js` / `toLocaleString('pt-BR')`).
7. **Gradiente/sombra:** com parcimônia e apenas semânticos (ex.: card de métrica
   principal com `from-primary/5`). Nada de gradiente/sombra decorativos em tudo.

## Config de ambiente (não regride)
- `public/env-config.js` NÃO deve fixar URL. Deixar `REACT_APP_BACKEND_URL: ''`.
  Em produção o `docker-entrypoint.sh` regenera a partir da env do container;
  fora dela, cai para `.env` (build) ou `window.location.origin`.
