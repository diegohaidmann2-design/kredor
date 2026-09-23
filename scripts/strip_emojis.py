#!/usr/bin/env python3
"""
Remove emojis pictográficos de arquivos JS mantendo:
- linhas de templates de mensagem WhatsApp (contêm 'template_whatsapp') — conteúdo enviado ao cliente
- setas (→ ← etc, ranges 2190-21FF) usadas como separadores de texto

Uso: python3 scripts/strip_emojis.py <arquivo1.js> [arquivo2.js ...]
"""
import re, sys

EMOJI = re.compile(
    "([\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2934\u2935])[\uFE0F\u200D]?\\s?"
)
COMBINERS = re.compile("[\uFE0F\u200D]")

def process(path):
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    out, changed = [], 0
    for ln in lines:
        if "template_whatsapp" in ln:  # preserva conteúdo de mensagem
            out.append(ln); continue
        new = COMBINERS.sub("", EMOJI.sub("", ln))
        if new != ln:
            changed += 1
        out.append(new)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out)
    print(f"{path}: {changed} linhas alteradas")

if __name__ == "__main__":
    for p in sys.argv[1:]:
        process(p)
