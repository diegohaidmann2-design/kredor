"""Gera o PDF do dossiê de uma consulta (reportlab)."""
from io import BytesIO
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

SECTION_LABELS = {
    "dadosBasicos": "Dados Básicos", "rgHistorico": "RG (Histórico)", "carteiraHabilitacao": "CNH / Habilitação",
    "tituloHistorico": "Título de Eleitor", "cnsHistorico": "CNS (Cartão SUS)", "pisHistorico": "PIS / NIS",
    "codigoCtps": "CTPS", "alistamentoMilitar": "Alistamento Militar", "opiniaoPolitica": "Opinião Política",
    "poderAquisitivo": "Poder Aquisitivo", "serasaMosaic": "Serasa Mosaic", "telefonesHistorico": "Telefones",
    "emails": "E-mails", "redesSociais": "Redes Sociais", "enderecos": "Endereços", "curriculos": "Currículo",
    "empregos": "Empregos / Vínculos", "empresas": "Empresas", "beneficios": "Benefícios", "dividas": "Dívidas",
    "vacinas": "Vacinas", "parentesNovos": "Parentes", "compras": "Compras", "cartoesUsados": "Cartões",
    "internet": "Presença na Internet", "imoveis": "Imóveis", "irpf": "IRPF", "veiculos": "Veículos",
    "processos": "Processos", "interesses": "Interesses", "consumos": "Consumos", "filiacao": "Filiação",
    "situacaoCadastral": "Situação Cadastral", "biometria": "Biometria",
}

EMPTY = {"", "não informado", "nao informado", "null", "none", "inexistente", "n/a", "na", "não consta", "nao consta", "sem informação", "sem informacao"}
IGNORE_KEYS = {"tipo"}


def _prettify(key):
    if key in SECTION_LABELS:
        return SECTION_LABELS[key]
    import re
    s = re.sub(r"_", " ", str(key))
    s = re.sub(r"([a-z\d])([A-Z])", r"\1 \2", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:1].upper() + s[1:] if s else s


def _empty(v):
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip().lower() in EMPTY
    if isinstance(v, list):
        return all(_empty(x) for x in v)
    if isinstance(v, dict):
        return all(k in IGNORE_KEYS or _empty(val) for k, val in v.items())
    return False


def _limpar(v):
    """Remove valores vazios/INEXISTENTE e itens de lista sem dados úteis (só 'tipo')."""
    if isinstance(v, list):
        return [x for x in (_limpar(i) for i in v) if not _empty(x)]
    if isinstance(v, dict):
        out = {}
        for k, val in v.items():
            cv = _limpar(val) if isinstance(val, (list, dict)) else val
            if not _empty(cv):
                out[k] = cv
        return out
    return v


def _kv_rows(obj, prefix=""):
    """Achata um dict em linhas [rótulo, valor], expandindo 1 nível de aninhamento."""
    rows = []
    for k, v in obj.items():
        if _empty(v):
            continue
        label = (prefix + " · " if prefix else "") + _prettify(k)
        if isinstance(v, dict):
            rows.extend(_kv_rows(v, _prettify(k)))
        elif isinstance(v, list):
            if v and isinstance(v[0], dict):
                rows.append([label, f"{len(v)} registro(s) — ver seção"])
            else:
                rows.append([label, ", ".join(str(x) for x in v if not _empty(x))])
        elif isinstance(v, bool):
            rows.append([label, "Sim" if v else "Não"])
        else:
            rows.append([label, str(v)])
    return rows


def gerar_pdf_consulta(consulta: dict) -> BytesIO:
    tipo = (consulta.get("tipo") or "cpf").lower()
    data = _limpar(consulta.get("data") or {})

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=1.5 * cm, rightMargin=1.5 * cm, title="Dossiê de Consulta")
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#0f766e"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, textColor=colors.HexColor("#0f766e"),
                        spaceBefore=10, spaceAfter=4)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8.5, leading=11)
    cell_lbl = ParagraphStyle("cell_lbl", parent=cell, textColor=colors.HexColor("#475569"))

    titulos = {"cpf": "CPF", "cpf-premium": "CPF Premium", "cnpj": "CNPJ", "telefone": "Telefone"}
    story = []
    story.append(Paragraph(f"Dossiê de Consulta — {titulos.get(tipo, tipo.upper())}", h1))
    gerado = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    story.append(Paragraph(f"Gerado por Kredor em {gerado}", small))
    story.append(Spacer(1, 8))

    # ===== CPF Premium: identidade + seções (campos/tabela) =====
    if tipo == "cpf-premium":
        dados = data.get("dados") or {}
        ident = [
            ["Nome", dados.get("nome") or "—"],
            ["CPF", consulta.get("documento") or dados.get("documento") or "—"],
            ["Nascimento", dados.get("nascimento") or "—"],
            ["Nome da Mãe", dados.get("nome_mae") or "—"],
            ["Sexo", dados.get("sexo") or "—"],
            ["Situação Cadastral", dados.get("situacao_cadastral") or "—"],
            ["Renda", dados.get("renda") or "—"],
            ["Profissão", dados.get("profissao") or "—"],
        ]
        t = Table([[Paragraph(a, cell_lbl), Paragraph(str(b), cell)] for a, b in ident], colWidths=[4 * cm, 13 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdfa")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#99f6e4")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ccfbf1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)

        for secao in (dados.get("secoes") or []):
            if not isinstance(secao, dict):
                continue
            blocos = secao.get("blocos") or []
            story.append(Paragraph(str(secao.get("titulo") or "Seção"), h2))
            rendered_any = False
            for bloco in blocos:
                if not isinstance(bloco, dict):
                    continue
                if bloco.get("tipo") == "tabela":
                    cols = [c for c in (bloco.get("colunas") or [])]
                    linhas = bloco.get("linhas") or []
                    if not cols and linhas and isinstance(linhas[0], dict):
                        cols = list(linhas[0].keys())
                    if not cols or not linhas:
                        continue
                    header = [Paragraph(str(c), cell_lbl) for c in cols]
                    body_rows = [[Paragraph(str(l.get(c, "") or ""), cell) for c in cols]
                                 for l in linhas if isinstance(l, dict)]
                    tbl = Table([header] + body_rows, repeatRows=1)
                    tbl.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ]))
                    story.append(tbl)
                    story.append(Spacer(1, 4))
                    rendered_any = True
                else:
                    campos = bloco.get("dados") or {}
                    rows = [[k, str(v)] for k, v in campos.items() if not _empty(v)]
                    if not rows:
                        continue
                    tbl = Table([[Paragraph(a, cell_lbl), Paragraph(b, cell)] for a, b in rows], colWidths=[6 * cm, 11 * cm])
                    tbl.setStyle(TableStyle([
                        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ]))
                    story.append(tbl)
                    story.append(Spacer(1, 4))
                    rendered_any = True
            if not rendered_any:
                story.append(Paragraph("Sem dados detalhados.", small))

        story.append(Spacer(1, 12))
        story.append(Paragraph(
            "Documento gerado automaticamente para fins de análise de crédito. Dados fornecidos por consulta cadastral.",
            small))
        doc.build(story)
        buf.seek(0)
        return buf

    # Cabeçalho de identidade (varia por tipo)
    if tipo == "cnpj":
        emp = data.get("dadosEmpresa") or {}
        ident = [
            ["Razão Social", emp.get("razaoSocial") or "—"],
            ["CNPJ", consulta.get("documento") or "—"],
            ["Natureza Jurídica", emp.get("naturezaJuridica") or "—"],
            ["Porte", emp.get("porteEmpresa") or "—"],
            ["Capital Social", emp.get("capitalSocial") or "—"],
            ["Responsável", emp.get("qualificacaoResponsavel") or "—"],
        ]
    elif tipo == "telefone":
        lista = data.get("data") if isinstance(data.get("data"), list) else []
        ident = [
            ["Telefone", consulta.get("documento") or "—"],
            ["Resultados", str(len(lista))],
        ]
    else:
        basicos = data.get("dadosBasicos") or {}
        ident = [
            ["Nome", basicos.get("nome") or "—"],
            ["CPF", consulta.get("documento") or basicos.get("cpf") or ""],
            ["Nascimento", basicos.get("dataNasc") or "—"],
            ["Faixa de Score", basicos.get("faixaScore") or "—"],
            ["Renda Atual", (f"R$ {basicos.get('rendaAtual')}" if basicos.get("rendaAtual") else "—")],
            ["Situação", (basicos.get("situacaoCadastral") or {}).get("descricaoSit") or "—"],
        ]
    t = Table([[Paragraph(a, cell_lbl), Paragraph(str(b), cell)] for a, b in ident], colWidths=[4 * cm, 13 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdfa")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#99f6e4")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ccfbf1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    # Demais seções
    skip_key = "dadosBasicos" if tipo == "cpf" else ("dadosEmpresa" if tipo == "cnpj" else None)
    for key, value in data.items():
        if key == skip_key or _empty(value):
            continue
        story.append(Paragraph(_prettify(key), h2))

        blocos = value if isinstance(value, list) else [value]
        rendered_any = False
        for bloco in blocos:
            if isinstance(bloco, dict):
                rows = _kv_rows(bloco)
            elif not _empty(bloco):
                rows = [["", str(bloco)]]
            else:
                rows = []
            if not rows:
                continue
            rendered_any = True
            tbl = Table([[Paragraph(a, cell_lbl), Paragraph(b, cell)] for a, b in rows], colWidths=[5 * cm, 12 * cm])
            tbl.setStyle(TableStyle([
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 4))
        if not rendered_any:
            story.append(Paragraph("Sem dados detalhados.", small))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Documento gerado automaticamente para fins de análise de crédito. Dados fornecidos por consulta cadastral.",
        small))

    doc.build(story)
    buf.seek(0)
    return buf
