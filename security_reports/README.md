# Scan Semgrep — GestorCred

**Comando:** `semgrep --config auto .`
**Data:** 2026-09-05

## Resultado
- Scan inicial: **15 findings** (8 ERROR, 6 WARNING, 1 INFO)
- Após correção: **14 findings** (todos falsos positivos ou fora do código da aplicação)

## Corrigido (1 vulnerabilidade REAL)

### 🛡️ `backend/services/backup_service.py` — TAR path traversal (CVE-2007-4559)
`tarfile.extractall()` sem sanitização permitia que um `.tar.gz` malicioso enviado
para restore escrevesse arquivos fora do diretório temporário (Zip Slip via tar).

**Fix:** validação manual de cada `TarInfo`:
- Rejeita entradas cujo caminho resolvido saia do `temp_dir`
- Rejeita symlinks / hardlinks / dispositivos / FIFOs
- Não altera comportamento para backups legítimos gerados pelo próprio sistema

Confirmação: revalidação pós-fix retornou 0 findings em `backup_service.py`.

## Falsos positivos (14 findings) — não alterados por design

| Arquivo | Rule | Motivo |
|---------|------|--------|
| `.emergent/summary.txt` | detected-jwt-token | Metadados do runtime Emergent (não é código) |
| `backend/.env example.example` | detected-mailgun-api-key | Arquivo de EXEMPLO com placeholder |
| `test_reports/emprestimo_500_error_test.json` (x3) | detected-jwt-token | Tokens de teste antigos em relatório JSON |
| `frontend/Dockerfile:62,63` | missing-user | Dockerfile não usado em produção Emergent (supervisor local) |
| `frontend/plugins/visual-edits/*.js` (x7) | path-traversal / unsafe-formatstring | Plugin interno Emergent, executa só em dev |

## Como reproduzir
```bash
/root/.venv/bin/python -m pip install semgrep
cd /app && /root/.venv/bin/semgrep --config auto \
  --exclude node_modules --exclude .venv --exclude __pycache__ \
  --exclude build --exclude dist --exclude .git \
  --exclude security_reports .
```

Relatórios completos em JSON:
- `/app/security_reports/scan_initial.json`
- `/app/security_reports/scan_after_fix.json`
