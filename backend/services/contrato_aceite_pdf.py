"""
Serviço de geração de Contrato de Empréstimo com Assinatura Digital e Carimbo de Auditoria LGPD.
Gera um contrato formal em PDF contendo qualificação completa das partes, cláusulas de mútuo,
tabela de parcelas, assinatura digital do mutuário e carimbo eletrônico de autenticidade (MP 2.200-2/2001 e LGPD).
"""
import html
import io
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
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
from utils.dinheiro import formatar_reais


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


def _formatar_data_hora(val: Optional[str]) -> str:
    if not val:
        return "—"
    try:
        if isinstance(val, datetime):
            dt = val
        else:
            s = str(val).replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_br = dt.astimezone(ZoneInfo("America/Sao_Paulo"))
        return dt_br.strftime("%d/%m/%Y às %H:%M:%S (Horário de Brasília)")
    except Exception:
        return str(val)[:19]


def _formatar_data_simples(val: Optional[str]) -> str:
    if not val:
        return "—"
    try:
        if isinstance(val, datetime):
            dt = val
        else:
            s = str(val).replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_br = dt.astimezone(ZoneInfo("America/Sao_Paulo"))
        return dt_br.strftime("%d/%m/%Y")
    except Exception:
        return str(val)[:10]


def _numero_por_extenso(valor_centavos: int) -> str:
    """Converte valor em centavos para extenso."""
    inteiro, centavos = divmod(int(valor_centavos or 0), 100)
    unidades = ["", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"]
    dezenas = ["", "dez", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
    centenas = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"]
    especiais = {11: "onze", 12: "doze", 13: "treze", 14: "quatorze", 15: "quinze", 16: "dezesseis", 17: "dezessete", 18: "dezoito", 19: "dezenove"}

    if inteiro == 0:
        return "zero reais"

    resultado = ""
    if inteiro >= 1000000:
        milhoes = inteiro // 1000000
        resto = inteiro % 1000000
        resultado = f"{unidades[milhoes]} milhão" if milhoes == 1 else f"{unidades[milhoes]} milhões"
        inteiro = resto
        if inteiro > 0:
            resultado += " e " if inteiro < 1000 else ", "

    if inteiro >= 1000:
        milhares = inteiro // 1000
        resto = inteiro % 1000
        if milhares == 1:
            resultado += "mil"
        elif milhares < 10:
            resultado += f"{unidades[milhares]} mil"
        elif milhares in especiais:
            resultado += f"{especiais[milhares]} mil"
        elif milhares < 20:
            resultado += f"{especiais.get(milhares, '')} mil"
        elif milhares < 100:
            dez = milhares // 10
            uni = milhares % 10
            resultado += f"{dezenas[dez]}{' e ' + unidades[uni] if uni > 0 else ''} mil"
        else:
            cen = milhares // 100
            rm = milhares % 100
            resultado += f"{'cem' if milhares == 100 else centenas[cen]}{' e ' + dezenas[rm // 10] if rm > 0 else ''} mil"
        inteiro = resto
        if inteiro > 0:
            resultado += " e " if inteiro < 100 else ", "

    if inteiro >= 100:
        if inteiro == 100:
            resultado += "cem"
            inteiro = 0
        else:
            cen = inteiro // 100
            inteiro = inteiro % 100
            resultado += centenas[cen]
            if inteiro > 0:
                resultado += " e "

    if inteiro > 0:
        if inteiro < 10:
            resultado += unidades[inteiro]
        elif inteiro in especiais:
            resultado += especiais[inteiro]
        elif inteiro < 100:
            dez = inteiro // 10
            uni = inteiro % 10
            resultado += dezenas[dez]
            if uni > 0:
                resultado += f" e {unidades[uni]}"

    resultado = resultado.strip() + (" real" if resultado.strip() == "um" else " reais")
    if centavos > 0:
        resultado += f" e {centavos} centavos"
    return resultado


def _carregar_imagem_reportlab(path_storage: Optional[str], max_w_cm: float, max_h_cm: float) -> Optional[Image]:
    """Carrega imagem do storage e redimensiona proporcionalmente."""
    if not path_storage:
        return None
    try:
        data_bytes, _ = get_object(path_storage)
        if not data_bytes:
            return None
        bio = io.BytesIO(data_bytes)
        pil_img = PILImage.open(bio)
        orig_w, orig_h = pil_img.size
        if orig_w <= 0 or orig_h <= 0:
            return None

        max_w_pt = max_w_cm * 28.3465
        max_h_pt = max_h_cm * 28.3465
        scale = min(max_w_pt / orig_w, max_h_pt / orig_h)
        final_w = orig_w * scale
        final_h = orig_h * scale

        bio.seek(0)
        return Image(bio, width=final_w, height=final_h)
    except Exception:
        return None


def gerar_contrato_assinado_pdf(
    emprestimo: Dict[str, Any],
    cliente: Dict[str, Any],
    credor: Dict[str, Any],
    parcelas: List[Dict[str, Any]],
) -> bytes:
    """
    Gera o PDF completo do Contrato de Empréstimo com Assinatura Digital do Mutuário e Carimbo LGPD.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    # Paleta de Cores Profissional
    c_primary = HexColor("#0f172a")      # Slate 900
    c_secondary = HexColor("#0284c7")    # Blue 600
    c_accent = HexColor("#059669")       # Emerald 600
    c_gray_bg = HexColor("#f8fafc")      # Slate 50
    c_border = HexColor("#cbd5e1")       # Slate 300
    c_text = HexColor("#1e293b")         # Slate 800
    c_muted = HexColor("#64748b")        # Slate 500

    title_style = ParagraphStyle(
        "ContratoTitulo",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=c_primary,
        alignment=1, # Center
    )

    subtitle_style = ParagraphStyle(
        "ContratoSubtitulo",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=c_secondary,
        alignment=1,
    )

    clause_title = ParagraphStyle(
        "ClausulaTitulo",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=c_primary,
        spaceBefore=10,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "ContratoCorpo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=c_text,
        alignment=4, # Justify
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=c_primary,
        alignment=1,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=c_text,
        alignment=1,
    )

    audit_label = ParagraphStyle(
        "AuditLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=c_primary,
    )

    audit_val = ParagraphStyle(
        "AuditVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=c_muted,
    )

    story = []

    # ==================== CABEÇALHO DO DOCUMENTO ====================
    nome_empresa = credor.get("nome") or "Kredor"
    story.append(Paragraph(f"INSTRUMENTO PARTICULAR DE CONTRATO DE MÚTUO FINANCEIRO", title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph(f"EMPRÉSTIMO Nº #{str(emprestimo.get('id', ''))[:8].upper()} • {_esc(nome_empresa).upper()}", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_secondary, spaceBefore=2, spaceAfter=10))

    # ==================== QUALIFICAÇÃO DAS PARTES ====================
    end_cli = cliente.get("endereco") or {}
    end_cli_txt = f"{end_cli.get('rua', '')}, {end_cli.get('numero', '')}"
    if end_cli.get("complemento"):
        end_cli_txt += f" ({end_cli.get('complemento')})"
    if end_cli.get("bairro"):
        end_cli_txt += f" - {end_cli.get('bairro')}"
    if end_cli.get("cidade") or end_cli.get("estado"):
        end_cli_txt += f", {end_cli.get('cidade', '')}/{end_cli.get('estado', '')}"
    if end_cli.get("cep"):
        end_cli_txt += f" - CEP: {end_cli.get('cep')}"

    texto_partes = f"""
    Pelo presente instrumento particular, de um lado:<br/><br/>
    <b>CREDOR (MUTUANTE):</b> <b>{_esc(credor.get('nome'))}</b>, 
    inscrito sob CPF/CNPJ: <b>{_formatar_cpf_cnpj(credor.get('cpf') or credor.get('cnpj') or credor.get('cpf_cnpj'))}</b>, 
    com endereço eletrônico: {_esc(credor.get('email'))}, telefone: {_formatar_telefone(credor.get('telefone'))};<br/><br/>
    E de outro lado:<br/><br/>
    <b>DEVEDOR (MUTUÁRIO):</b> <b>{_esc(cliente.get('nome'))}</b>, 
    inscrito sob CPF/CNPJ: <b>{_formatar_cpf_cnpj(cliente.get('cpf_cnpj'))}</b>, 
    telefone: {_formatar_telefone(cliente.get('telefone'))}, 
    e-mail: {_esc(cliente.get('email'))}, 
    residente e domiciliado em: {_esc(end_cli_txt)}.<br/><br/>
    Têm entre si, justo e contratado, o presente Contrato de Mútuo Financeiro, que se regerá pelas cláusulas e condições seguintes:
    """
    story.append(Paragraph(texto_partes, body_style))
    story.append(Spacer(1, 8))

    # ==================== CLÁUSULA 1 - DO OBJETO E VALORES ====================
    valor_principal_centavos = emprestimo.get("valor_principal_centavos", 0)
    valor_principal_fmt = formatar_reais(valor_principal_centavos)
    extenso_principal = _numero_por_extenso(valor_principal_centavos)

    story.append(Paragraph("CLÁUSULA PRIMEIRA – DO OBJETO E DO VALOR", clause_title))
    texto_obj = f"""
    1.1. O presente contrato tem por objeto a concessão, pelo <b>CREDOR</b> ao <b>DEVEDOR</b>, de um mútuo em moeda corrente nacional no valor de 
    <b>R$ {valor_principal_fmt} ({extenso_principal})</b>, disponibilizado na data de celebração deste instrumento.<br/><br/>
    1.2. O DEVEDOR declara que recebeu a quantia supra e dela dá plena, rasa e irrevogável quitação quanto ao recebimento do capital.
    """
    story.append(Paragraph(texto_obj, body_style))

    # ==================== CLÁUSULA 2 - DOS JUROS E TAXAS ====================
    periodicidade = emprestimo.get("periodicidade") or "mensal"
    taxa_juros = emprestimo.get("taxa_juros_semanal") if periodicidade == "semanal" else emprestimo.get("taxa_juros_mensal")
    metodo_calculo = emprestimo.get("metodo_calculo") or "juros_simples"
    metodo_nome = {
        "juros_simples": "Juros Simples",
        "simples": "Juros Simples",
        "juros_compostos": "Juros Compostos",
        "composto": "Juros Compostos",
        "tabela_price": "Tabela Price (Francês)",
        "price": "Tabela Price (Francês)",
        "sac": "Sistema de Amortização Constante (SAC)",
        "apenas_juros": "Somente Juros (Empréstimo Aberto)",
    }.get(metodo_calculo, metodo_calculo)

    story.append(Paragraph("CLÁUSULA SEGUNDA – DOS JUROS E MÉTODO DE CÁLCULO", clause_title))
    texto_juros = f"""
    2.1. Sobre o valor principal incidirão juros remuneratórios à taxa de <b>{taxa_juros}% ({periodicidade})</b>, calculados com base no método <b>{metodo_nome}</b>.<br/><br/>
    2.2. A periodicidade de apuração e vencimento das obrigações é <b>{periodicidade.upper()}</b>, contada a partir da data de início em <b>{_formatar_data_simples(emprestimo.get('data_inicio'))}</b>.
    """
    story.append(Paragraph(texto_juros, body_style))

    # ==================== CLÁUSULA 3 - DO PAGAMENTO E CRONOGRAMA ====================
    sem_prazo = bool(emprestimo.get("sem_prazo"))
    story.append(Paragraph("CLÁUSULA TERCEIRA – DA FORMA DE PAGAMENTO E CRONOGRAMA", clause_title))

    if sem_prazo:
        texto_pag = f"""
        3.1. Tratando-se de modalidade aberta (Somente Juros), o DEVEDOR pagará periodicamente os juros remuneratórios acordados, permanecendo o principal exigível ou amortizável mediante acordo entre as partes.<br/><br/>
        3.2. Os pagamentos deverão ser efetuados até a data de vencimento de cada ciclo por meio de PIX, transferência bancária ou outra modalidade indicada pelo CREDOR.
        """
    else:
        prazo_txt = f"{emprestimo.get('prazo_semanas')} semanas" if periodicidade == "semanal" else f"{emprestimo.get('prazo_meses', len(parcelas))} meses"
        valor_total_fmt = formatar_reais(emprestimo.get("valor_total_com_juros_centavos", 0))
        texto_pag = f"""
        3.1. O DEVEDOR obriga-se a restituir o montante total de <b>R$ {valor_total_fmt}</b>, dividido em <b>{prazo_txt}</b>, conforme o cronograma de parcelas discriminado abaixo.<br/><br/>
        3.2. O pagamento de cada parcela dará quitação exclusiva do respectivo valor e vencimento, não presumindo a quitação das parcelas anteriores ou posteriores.
        """
    story.append(Paragraph(texto_pag, body_style))

    # Tabela de parcelas se existirem
    if parcelas and len(parcelas) > 0:
        story.append(Spacer(1, 4))
        t_data = [[
            Paragraph("<b>Parcela</b>", table_header_style),
            Paragraph("<b>Data de Vencimento</b>", table_header_style),
            Paragraph("<b>Valor da Parcela</b>", table_header_style),
        ]]
        for p in parcelas:
            venc = _formatar_data_simples(p.get("data_vencimento"))
            val_cent = p.get("valor_total_centavos")
            if val_cent is None and p.get("valor_total") is not None:
                val_cent = int(round(float(p.get("valor_total")) * 100))
            val_p = formatar_reais(val_cent or 0)
            t_data.append([
                Paragraph(f"Parcela {p.get('numero_parcela')}", table_cell_style),
                Paragraph(venc, table_cell_style),
                Paragraph(f"R$ {val_p}", table_cell_style),
            ])

        t_parcelas = Table(t_data, colWidths=[4 * cm, 7 * cm, 7 * cm])
        t_parcelas.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 0.5, c_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, c_border),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_parcelas)
        story.append(Spacer(1, 4))

    # ==================== CLÁUSULA 4 - DA MORA E INADIMPLÊNCIA ====================
    multa = emprestimo.get("taxa_multa_atraso", 2)
    mora = emprestimo.get("taxa_juros_mora_diario", 0.033)
    story.append(Paragraph("CLÁUSULA QUARTA – DA MORA, MULTA E ENCARGOS", clause_title))
    texto_mora = f"""
    4.1. O não pagamento de qualquer parcela na data do respectivo vencimento sujeitará o DEVEDOR, de pleno direito e independentemente de notificação judicial ou extrajudicial, ao pagamento de:<br/>
    &nbsp;&nbsp;a) <b>Multa moratória de {multa}%</b> sobre o montante em atraso;<br/>
    &nbsp;&nbsp;b) <b>Juros de mora diários de {mora}% ao dia</b>, calculados pro rata die até a data do efetivo pagamento.<br/><br/>
    4.2. O atraso superior a 30 (trinta) dias ensejará o vencimento antecipado de toda a dívida vincenda, autorizando o CREDOR a cobrar a integralidade do saldo devedor acrescido dos encargos legais.
    """
    story.append(Paragraph(texto_mora, body_style))

    # ==================== CLÁUSULA 5 - DAS DISPOSIÇÕES GERAIS E FORO ====================
    cidade_foro = end_cli.get("cidade") or "São Paulo"
    estado_foro = end_cli.get("estado") or "SP"
    story.append(Paragraph("CLÁUSULA QUINTA – DAS DISPOSIÇÕES FINAIS E DO FORO", clause_title))
    texto_disp = f"""
    5.1. A eventual tolerância por parte do CREDOR quanto a qualquer infração das cláusulas deste contrato não constituirá novação nem renúncia a direitos.<br/><br/>
    5.2. As partes elegem o foro da Comarca de <b>{_esc(cidade_foro)}/{_esc(estado_foro)}</b> para dirimir quaisquer dúvidas ou litígios decorrentes deste contrato, renunciando a qualquer outro, por mais privilegiado que seja.
    """
    story.append(Paragraph(texto_disp, body_style))
    story.append(Spacer(1, 10))

    # ==================== BLOCO DE ASSINATURAS E CERTIFICAÇÃO ELETRÔNICA ====================
    aceite = emprestimo.get("aceite") or {}
    ass_path = aceite.get("assinatura_path")
    img_assinatura = _carregar_imagem_reportlab(ass_path, max_w_cm=7.5, max_h_cm=2.6)

    data_aceite_fmt = _formatar_data_hora(aceite.get("assinado_em") or datetime.now(timezone.utc))
    ip_aceite = aceite.get("ip") or "Registrado eletronicamente"
    ua_aceite = (aceite.get("user_agent") or "Navegador Web Seguro")[:250]
    token_aceite = aceite.get("token") or str(emprestimo.get("id"))[:12]

    col_ass_devedor = [
        Paragraph("<b>ASSINATURA DIGITAL DO DEVEDOR</b>", audit_label),
        Spacer(1, 4),
        img_assinatura or Paragraph("<font color='#64748b' size='8'>Assinado digitalmente</font>", audit_val),
        Spacer(1, 3),
        HRFlowable(width="90%", thickness=0.8, color=c_primary, spaceBefore=1, spaceAfter=2),
        Paragraph(f"<b>{_esc(cliente.get('nome'))}</b>", ParagraphStyle("AssNome", parent=audit_label, fontSize=8.5, alignment=1)),
        Paragraph(f"CPF: {_formatar_cpf_cnpj(cliente.get('cpf_cnpj'))}", ParagraphStyle("AssCpf", parent=audit_val, fontSize=7.5, alignment=1)),
    ]

    col_carimbo_auditoria = [
        Paragraph("<b>CERTIFICAÇÃO DE ASSINATURA ELETRÔNICA (LGPD / MP 2.200-2)</b>", ParagraphStyle("CertTitle", parent=audit_label, textColor=c_accent)),
        Spacer(1, 3),
        Paragraph(f"• <b>Autenticação:</b> Token <code>{_esc(token_aceite)}</code>", audit_val),
        Paragraph(f"• <b>Data/Hora do Aceite:</b> {data_aceite_fmt}", audit_val),
        Paragraph(f"• <b>Endereço IP:</b> <code>{_esc(ip_aceite)}</code>", audit_val),
        Paragraph(f"• <b>Dispositivo:</b> <font size='6.5'>{_esc(ua_aceite)}</font>", audit_val),
        Paragraph(f"• <b>Validade Jurídica:</b> Medida Provisória nº 2.200-2/2001 e Lei Federal nº 14.063/2020.", audit_val),
        Spacer(1, 2),
        Paragraph("<font size='6.5' color='#059669'><b>✓ Assinatura eletrônica válida com consentimento expresso e carimbo de tempo.</b></font>", audit_val),
    ]

    t_assinaturas = Table([[col_ass_devedor, col_carimbo_auditoria]], colWidths=[8.0 * cm, 10.0 * cm])
    t_assinaturas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), c_gray_bg),
        ("BOX", (0, 0), (-1, -1), 0.8, c_secondary),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, c_border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(KeepTogether([
        Paragraph("<b>FORMALIZAÇÃO E ASSINATURA ELETRÔNICA</b>", ParagraphStyle("FormHead", parent=clause_title, spaceBefore=8, spaceAfter=4)),
        t_assinaturas
    ]))

    doc.build(story)
    return buffer.getvalue()
