# Credenciais de Teste - Gestor Cred

## Usuarios do Sistema

### Administrador Principal (Enterprise)
- **Email:** diego.haidmann@gmail.com
- **Senha:** muda2025
- **Perfil:** Admin
- **Plano:** Enterprise
- **Status:** Ativo

### Admin do Sistema (Enterprise)
- **Email:** admin@gestorcerd.com
- **Senha:** admin123
- **Perfil:** Admin
- **Plano:** Enterprise
- **Status:** Ativo

### Usuario Comum (Profissional)
- **Email:** usuario@teste.com
- **Senha:** senha123
- **Perfil:** Usuario
- **Plano:** Profissional
- **Status:** Ativo

---

## URL do Sistema
**https://credito-concluido.preview.emergentagent.com**

## API Login
- Campo de senha no login: `senha` (nao `password`)
- Resposta do login retorna `usuario` (nao `user`)

---

## Notas
- Todos os usuarios foram criados pelo seeder
- Email ja esta verificado para todos
- Trial valido por 365 dias (admins) ou 30 dias (usuarios)
- Ultima atualizacao: 2026-04-12
- SyncPay gateway configurado como strategy: syncpay_only
