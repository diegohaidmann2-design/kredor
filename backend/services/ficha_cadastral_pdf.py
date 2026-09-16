"""
Serviço de geração de Ficha Cadastral em PDF (ReportLab).
Gera um dossiê completo da solicitação de cadastro contendo dados pessoais,
endereço, fotos (selfie, doc frente/verso), assinatura digital e carimbo de auditoria LGPD.
"""
import html
import io
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from PIL import Image as PILImage
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from services.object_storage import get_object


def _esc(val: Any) -> str:
    """Escapa texto para inclusão segura em Paragraph do ReportLab."""
    if val is None:
        return "—"
    s = str(val).strip()
    return html.escape(s) if s else "—"


def _formatar_cpf_cnpj(val: Optional[str]) -> str:
    if not val:
        return "—"
    dig = re.sub(r"\D", "", str(val))
    if len(dig) == 11:
        return f"{dig[:3]}.{dig[3:6]}.{dig[6:9]}-{dig[9:]}"
    if len(dig) == 14:
        return f"{dig[:2]}.{dig[2:5]}.{dig[5:8]}/{dig[8:12]}-{dig[12:]}"
    return str(val)


def _formatar_telefone(val: Optional[str]) -> str:
    if not val:
        return "—"
    dig = re.sub(r"\D", "", str(val))
    if len(dig) == 11:
        return f"({dig[:2]}) {dig[2:7]}-{dig[7:]}"
    if len(dig) == 10:
        return f"({dig[:2]}) {dig[2:6]}-{dig[6:]}"
    return str(val)


def _formatar_data(val: Optional[str]) -> str:
    if not val:
        return "—"
    try:
        if isinstance(val, datetime):
            dt = val
        else:
            s = str(val).replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
        # Converter UTC → America/Sao_Paulo
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_br = dt.astimezone(ZoneInfo("America/Sao_Paulo"))
        return dt_br.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(val)[:19]


def _carregar_imagem_reportlab(path_storage: Optional[str], max_w_cm: float, max_h_cm: float) -> Optional[Image]:
    """
    Carrega imagem do object_storage, calcula redimensionamento proporcional e retorna reportlab.platypus.Image.
    """
    if not path_storage:
        return None
    try:
        data_bytes, _ = get_object(path_storage)
        if not data_bytes:
            return None

        # Abrir com Pillow para pegar dimensões
        bio = io.BytesIO(data_bytes)
        pil_img = PILImage.open(bio)
        orig_w, orig_h = pil_img.size
        if orig_w <= 0 or orig_h <= 0:
            return None

        # Converter limites em pontos (1 cm = 28.3465 pt)
        max_w_pt = max_w_cm * 28.3465
        max_h_pt = max_h_cm * 28.3465

        # Calcular escala
        scale = min(max_w_pt / orig_w, max_h_pt / orig_h)
        target_w = orig_w * scale
        target_h = orig_h * scale

        bio.seek(0)
        img = Image(bio, width=target_w, height=target_h)
        return img
    except Exception:
        return None


def gerar_ficha_cadastral_pdf(solicitacao: Dict[str, Any], empresa_nome: Optional[str] = None) -> bytes:
    """
    Constrói e retorna o PDF em bytes da ficha cadastral.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Ficha Cadastral - {solicitacao.get('nome', 'Cliente')}",
        author=empresa_nome or "Kredor",
    )

    # Paleta de Cores Kredor
    c_primary = HexColor("#059669")     # Emerald 600
    c_dark = HexColor("#0f172a")        # Slate 900
    c_gray_dark = HexColor("#334155")   # Slate 700
    c_gray_light = HexColor("#f8fafc")  # Slate 50
    c_border = HexColor("#e2e8f0")      # Slate 200
    c_text_muted = HexColor("#64748b")  # Slate 500

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=c_dark,
    )
    subtitle_style = ParagraphStyle(
        "HeaderSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=c_text_muted,
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=c_primary,
    )
    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=c_text_muted,
    )
    val_style = ParagraphStyle(
        "ValStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=c_dark,
    )
    badge_style = ParagraphStyle(
        "BadgeStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=1,  # Center
    )
    audit_style = ParagraphStyle(
        "AuditStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=c_gray_dark,
    )

    story = []

    # ==================== 1. CABEÇALHO ====================
    status = str(solicitacao.get("status") or "pendente").lower()
    status_label = "PENDENTE" if status == "pendente" else "APROVADO" if status == "aprovado" else "REJEITADO"
    status_bg = HexColor("#fef3c7") if status == "pendente" else HexColor("#d1fae5") if status == "aprovado" else HexColor("#fee2e2")
    status_fg = HexColor("#92400e") if status == "pendente" else HexColor("#065f46") if status == "aprovado" else HexColor("#991b1b")

    badge_p = Paragraph(f'<font color="{status_fg.hexval()}">{status_label}</font>', badge_style)
    badge_table = Table([[badge_p]], colWidths=[2.6 * cm], rowHeights=[0.7 * cm])
    badge_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), status_bg),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, status_fg),
        ("BOX", (0, 0), (-1, -1), 0.5, status_fg),
    ]))

    header_left = [
        Paragraph(_esc(empresa_nome or "Kredor Gestão"), ParagraphStyle("EmpresaHeader", parent=title_style, fontSize=13, textColor=c_primary)),
        Paragraph("FICHA CADASTRAL DE CLIENTE & DOSSIÊ", title_style),
        Paragraph(f"Protocolo: <b>{solicitacao.get('id', '—')}</b> | Data de Envio: {_formatar_data(solicitacao.get('created_at'))}", subtitle_style),
    ]

    header_table = Table([[header_left, badge_table]], colWidths=[15 * cm, 3 * cm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceBefore=2, spaceAfter=8))

    # ==================== 2. DADOS PESSOAIS & CONTATO ====================
    story.append(Paragraph("1. DADOS PESSOAIS & CONTATO", section_title))
    story.append(Spacer(1, 0.15 * cm))

    cpf_formatado = _formatar_cpf_cnpj(solicitacao.get("cpf_cnpj"))
    tel_formatado = _formatar_telefone(solicitacao.get("telefone"))

    dados_pessoais = [
        [
            Paragraph("NOME COMPLETO", label_style),
            Paragraph("CPF / CNPJ", label_style),
            Paragraph("TELEFONE (WHATSAPP)", label_style),
        ],
        [
            Paragraph(f"<b>{_esc(solicitacao.get('nome'))}</b>", val_style),
            Paragraph(f"<b>{cpf_formatado}</b>", val_style),
            Paragraph(tel_formatado, val_style),
        ],
        [
            Paragraph("E-MAIL", label_style),
            Paragraph("ORIGEM DO CADASTRO", label_style),
            Paragraph("DATA DO REGISTRO", label_style),
        ],
        [
            Paragraph(_esc(solicitacao.get("email")), val_style),
            Paragraph(_esc(solicitacao.get("origem", "Link Público")), val_style),
            Paragraph(_formatar_data(solicitacao.get("created_at")), val_style),
        ],
    ]

    t_pessoais = Table(dados_pessoais, colWidths=[7.5 * cm, 5.2 * cm, 5.3 * cm])
    t_pessoais.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), c_gray_light),
        ("BOX", (0, 0), (-1, -1), 0.5, c_border),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, c_border),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_pessoais)
    story.append(Spacer(1, 0.3 * cm))

    # ==================== 3. ENDEREÇO ====================
    end = solicitacao.get("endereco") or {}
    story.append(Paragraph("2. ENDEREÇO RESIDENCIAL / COMERCIAL", section_title))
    story.append(Spacer(1, 0.15 * cm))

    dados_end = [
        [
            Paragraph("LOGRADOURO (RUA / AV)", label_style),
            Paragraph("Nº", label_style),
            Paragraph("COMPLEMENTO", label_style),
        ],
        [
            Paragraph(_esc(end.get("rua")), val_style),
            Paragraph(_esc(end.get("numero")), val_style),
            Paragraph(_esc(end.get("complemento")), val_style),
        ],
        [
            Paragraph("BAIRRO", label_style),
            Paragraph("CIDADE / UF", label_style),
            Paragraph("CEP", label_style),
        ],
        [
            Paragraph(_esc(end.get("bairro")), val_style),
            Paragraph(f"{_esc(end.get('cidade'))} - {_esc(end.get('estado'))}", val_style),
            Paragraph(_esc(end.get("cep")), val_style),
        ],
    ]

    t_end = Table(dados_end, colWidths=[8.5 * cm, 2.5 * cm, 7.0 * cm])
    t_end.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), c_gray_light),
        ("BOX", (0, 0), (-1, -1), 0.5, c_border),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, c_border),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_end)

    if solicitacao.get("observacoes"):
        story.append(Spacer(1, 0.2 * cm))
        t_obs = Table([
            [Paragraph("OBSERVAÇÕES INFORMADAS PELO CLIENTE", label_style)],
            [Paragraph(f'<i>"{_esc(solicitacao.get("observacoes"))}"</i>', val_style)],
        ], colWidths=[18 * cm])
        t_obs.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_gray_light),
            ("BOX", (0, 0), (-1, -1), 0.5, c_border),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t_obs)

    # ==================== 3. DADOS FINANCEIROS ====================
    renda = solicitacao.get("renda_mensal")
    tipo_emp = solicitacao.get("tipo_emprego")
    valor_emp = solicitacao.get("valor_emprestimo")

    if renda or tipo_emp or valor_emp:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("3. INFORMAÇÕES FINANCEIRAS", section_title))
        story.append(Spacer(1, 0.15 * cm))

        dados_fin = [
            [
                Paragraph("SITUAÇÃO DE EMPREGO", label_style),
                Paragraph("RENDA MENSAL", label_style),
                Paragraph("VALOR DO EMPRÉSTIMO DESEJADO", label_style),
            ],
            [
                Paragraph(_esc(tipo_emp), val_style),
                Paragraph(f"R$ {_esc(renda)}" if renda else "—", val_style),
                Paragraph(f"R$ {_esc(valor_emp)}" if valor_emp else "—", val_style),
            ],
        ]

        t_fin = Table(dados_fin, colWidths=[6 * cm, 5.5 * cm, 6.5 * cm])
        t_fin.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_gray_light),
            ("BOX", (0, 0), (-1, -1), 0.5, c_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, c_border),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t_fin)

    story.append(Spacer(1, 0.35 * cm))

    # ==================== 4. BIOMETRIA E DOCUMENTOS (FOTOS) ====================
    anexos = solicitacao.get("anexos") or {}
    selfie_info = anexos.get("selfie") if isinstance(anexos.get("selfie"), dict) else None
    frente_info = anexos.get("doc_frente") if isinstance(anexos.get("doc_frente"), dict) else None
    verso_info = anexos.get("doc_verso") if isinstance(anexos.get("doc_verso"), dict) else None
    ass_info = anexos.get("assinatura") if isinstance(anexos.get("assinatura"), dict) else None

    has_fotos = bool(selfie_info or frente_info or verso_info)
    has_financeiro = bool(renda or tipo_emp or valor_emp)

    if has_fotos:
        story.append(Paragraph("4. COMPROVAÇÃO DE IDENTIDADE & DOCUMENTOS", section_title))
        story.append(Spacer(1, 0.15 * cm))

        img_selfie = _carregar_imagem_reportlab(selfie_info.get("path") if selfie_info else None, max_w_cm=5.2, max_h_cm=5.5)
        img_frente = _carregar_imagem_reportlab(frente_info.get("path") if frente_info else None, max_w_cm=5.8, max_h_cm=5.5)
        img_verso = _carregar_imagem_reportlab(verso_info.get("path") if verso_info else None, max_w_cm=5.8, max_h_cm=5.5)

        col_selfie = [
            Paragraph("<b>🤳 FOTO DE ROSTO (SELFIE)</b>", label_style),
            Spacer(1, 3),
            img_selfie or Paragraph("<font color='#94a3b8'>Foto não enviada</font>", subtitle_style),
        ]
        col_frente = [
            Paragraph("<b>🪪 DOCUMENTO (FRENTE)</b>", label_style),
            Spacer(1, 3),
            img_frente or Paragraph("<font color='#94a3b8'>Foto não enviada</font>", subtitle_style),
        ]
        col_verso = [
            Paragraph("<b>🪪 DOCUMENTO (VERSO)</b>", label_style),
            Spacer(1, 3),
            img_verso or Paragraph("<font color='#94a3b8'>Foto não enviada</font>", subtitle_style),
        ]

        t_fotos = Table([[col_selfie, col_frente, col_verso]], colWidths=[5.6 * cm, 6.2 * cm, 6.2 * cm])
        t_fotos.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_gray_light),
            ("BOX", (0, 0), (-1, -1), 0.5, c_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, c_border),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_fotos)
        story.append(Spacer(1, 0.35 * cm))

    # ==================== 5. ASSINATURA DIGITAL & AUDITORIA LGPD ====================
    sec_num = str(4 + int(has_fotos) + int(has_financeiro))
    story.append(Paragraph(f"{sec_num}. ASSINATURA DIGITAL & TERMO LGPD", section_title))
    story.append(Spacer(1, 0.15 * cm))

    img_ass = _carregar_imagem_reportlab(ass_info.get("path") if ass_info else None, max_w_cm=7.5, max_h_cm=2.8)
    consent = solicitacao.get("consentimento") or {}

    col_assinatura = [
        Paragraph("<b>ASSINATURA ELETRÔNICA DO TITULAR</b>", label_style),
        Spacer(1, 4),
        img_ass or Paragraph("<font color='#94a3b8'>Assinatura não coletada</font>", subtitle_style),
        Spacer(1, 2),
        Paragraph(f"<b>{_esc(solicitacao.get('nome'))}</b>", ParagraphStyle("AssNome", parent=val_style, fontSize=8, alignment=1)),
    ]

    audit_lines = [
        Paragraph("<b>CARIMBO DE AUDITORIA E CONSENTIMENTO (LGPD)</b>", label_style),
        Spacer(1, 3),
        Paragraph(f"• <b>Status do Consentimento:</b> {'ACEITO EXPRESSAMENTE' if consent.get('aceito') else 'NÃO REGISTRADO'}", audit_style),
        Paragraph(f"• <b>Data e Hora do Aceite:</b> {_formatar_data(consent.get('aceito_em'))}", audit_style),
        Paragraph(f"• <b>Endereço IP Registrado:</b> <code>{_esc(consent.get('ip'))}</code>", audit_style),
        Paragraph(f"• <b>Dispositivo / Navegador:</b> <font size='6.5'>{_esc(consent.get('user_agent'))}</font>", audit_style),
        Paragraph(f"• <b>Termo / Versão:</b> {_esc(consent.get('versao_termo', 'v1-2026-09'))}", audit_style),
        Spacer(1, 2),
        Paragraph("<font size='6.5' color='#64748b'>Declaração: O titular autorizou expressamente o tratamento dos dados e envio de documentos para fins de análise cadastral e emissão de contratos conforme Lei nº 13.709/2018.</font>", audit_style),
    ]

    t_ass = Table([[col_assinatura, audit_lines]], colWidths=[8.0 * cm, 10.0 * cm])
    t_ass.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), c_gray_light),
        ("BOX", (0, 0), (-1, -1), 0.5, c_border),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, c_border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(KeepTogether(t_ass))

    # ==================== 6. RODAPÉ DE AUDITORIA ====================
    story.append(Spacer(1, 0.4 * cm))
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M:%S UTC")
    footer_text = Paragraph(
        f"<font size='7' color='#94a3b8'>Documento gerado eletronicamente pela plataforma Kredor em {now_str}. "
        f"Contém dados confidenciais e protegidos por sigilo profissional e LGPD. Protocolo: {solicitacao.get('id', '—')}</font>",
        ParagraphStyle("DocFooter", parent=styles["Normal"], alignment=1),
    )
    story.append(footer_text)

    # Construir PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
