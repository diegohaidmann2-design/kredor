"""
Templates profissionais para relatórios PDF
Design moderno com paleta de cores corporativa
"""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from datetime import datetime
from io import BytesIO


# Paleta de cores profissional - Azul corporativo
CORES = {
    'primaria': colors.HexColor('#1e40af'),      # Azul escuro
    'secundaria': colors.HexColor('#3b82f6'),    # Azul médio
    'acento': colors.HexColor('#60a5fa'),        # Azul claro
    'sucesso': colors.HexColor('#10b981'),       # Verde
    'alerta': colors.HexColor('#f59e0b'),        # Laranja
    'erro': colors.HexColor('#ef4444'),          # Vermelho
    'texto': colors.HexColor('#1f2937'),         # Cinza escuro
    'texto_claro': colors.HexColor('#6b7280'),   # Cinza médio
    'fundo': colors.HexColor('#f9fafb'),         # Cinza muito claro
    'borda': colors.HexColor('#e5e7eb'),         # Cinza claro
}


def criar_cabecalho(canvas, doc, titulo, periodo, empresa="Kredor"):
    """
    Cria cabeçalho profissional com logo, título e informações
    """
    canvas.saveState()
    
    # Fundo do cabeçalho
    canvas.setFillColor(CORES['primaria'])
    canvas.rect(0, A4[1] - 2*cm, A4[0], 2*cm, fill=1, stroke=0)
    
    # Nome da empresa
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica-Bold', 20)
    canvas.drawString(2*cm, A4[1] - 1.2*cm, empresa)
    
    # Título do relatório
    canvas.setFont('Helvetica', 12)
    canvas.drawString(2*cm, A4[1] - 1.7*cm, titulo)
    
    # Data de geração (canto direito)
    canvas.setFont('Helvetica', 9)
    # Formatação correta em português
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
             'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    agora = datetime.now()
    data_geracao = f"{agora.day:02d}/{agora.month:02d}/{agora.year} às {agora.hour:02d}:{agora.minute:02d}"
    canvas.drawRightString(A4[0] - 2*cm, A4[1] - 1.2*cm, f"Gerado em: {data_geracao}")
    
    # Período (canto direito)
    canvas.setFont('Helvetica-Bold', 9)
    canvas.drawRightString(A4[0] - 2*cm, A4[1] - 1.7*cm, f"Período: {periodo}")
    
    canvas.restoreState()


def criar_rodape(canvas, doc):
    """
    Cria rodapé profissional com número de página e informações
    """
    canvas.saveState()
    
    # Linha superior
    canvas.setStrokeColor(CORES['borda'])
    canvas.setLineWidth(1)
    canvas.line(2*cm, 1.5*cm, A4[0] - 2*cm, 1.5*cm)
    
    # Informações
    canvas.setFillColor(CORES['texto_claro'])
    canvas.setFont('Helvetica', 8)
    canvas.drawString(2*cm, 1*cm, "Kredor - Sistema de Gestão de Empréstimos")
    canvas.drawString(2*cm, 0.6*cm, "www.kredor.com.br")
    
    # Número da página
    canvas.drawRightString(A4[0] - 2*cm, 1*cm, f"Página {doc.page}")
    canvas.drawRightString(A4[0] - 2*cm, 0.6*cm, "Confidencial")
    
    canvas.restoreState()


def criar_card_metrica(titulo, valor, cor=CORES['primaria'], largura=5*cm, altura=2.5*cm):
    """
    Cria um card visual para exibir uma métrica
    """
    drawing = Drawing(largura, altura)
    
    # Fundo do card
    rect = Rect(0, 0, largura, altura, fillColor=cor, strokeColor=None)
    drawing.add(rect)
    
    # Título (mais compacto)
    titulo_str = String(largura/2, altura - 0.6*cm, titulo, 
                       fontSize=9, fillColor=colors.white, textAnchor='middle', fontName='Helvetica-Bold')
    drawing.add(titulo_str)
    
    # Valor (proporcionalmente menor)
    valor_str = String(largura/2, altura/2 - 0.2*cm, str(valor),
                      fontSize=14, fillColor=colors.white, textAnchor='middle', fontName='Helvetica-Bold')
    drawing.add(valor_str)
    
    return drawing


def criar_tabela_profissional(dados, headers=None, titulo_tabela=None):
    """
    Cria tabela com estilo profissional moderno
    """
    if not headers and dados:
        headers = list(dados[0].keys())
    
    # Preparar dados da tabela
    table_data = [headers] if headers else []
    for row in dados:
        if isinstance(row, dict):
            table_data.append([str(row.get(h, "")) for h in headers])
        else:
            table_data.append([str(v) for v in row])
    
    # Criar tabela
    table = Table(table_data, repeatRows=1)
    
    # Estilo profissional
    style = TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), CORES['primaria']),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Corpo da tabela
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        
        # Linhas alternadas
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, CORES['fundo']]),
        
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, CORES['borda']),
        ('BOX', (0, 0), (-1, -1), 1.5, CORES['primaria']),
        
        # Linha após cabeçalho
        ('LINEBELOW', (0, 0), (-1, 0), 2, CORES['primaria']),
    ])
    
    table.setStyle(style)
    
    return table


def criar_secao_titulo(texto, nivel=1):
    """
    Cria título de seção com estilo
    """
    styles = getSampleStyleSheet()
    
    if nivel == 1:
        style = ParagraphStyle(
            'SecaoTitulo1',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=CORES['primaria'],
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderColor=CORES['primaria'],
            borderPadding=0,
            leftIndent=0,
        )
    else:
        style = ParagraphStyle(
            'SecaoTitulo2',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=CORES['texto'],
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold',
        )
    
    return Paragraph(texto, style)


def criar_paragrafo(texto, estilo='normal'):
    """
    Cria parágrafo com estilo
    """
    styles = getSampleStyleSheet()
    
    if estilo == 'normal':
        style = ParagraphStyle(
            'Paragrafo',
            parent=styles['Normal'],
            fontSize=10,
            textColor=CORES['texto'],
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        )
    elif estilo == 'destaque':
        style = ParagraphStyle(
            'Destaque',
            parent=styles['Normal'],
            fontSize=11,
            textColor=CORES['primaria'],
            fontName='Helvetica-Bold',
            spaceAfter=10,
        )
    elif estilo == 'nota':
        style = ParagraphStyle(
            'Nota',
            parent=styles['Normal'],
            fontSize=9,
            textColor=CORES['texto_claro'],
            fontStyle='italic',
            spaceAfter=6,
        )
    else:
        style = styles['Normal']
    
    return Paragraph(texto, style)


def criar_linha_separadora(largura=None):
    """
    Cria linha separadora decorativa
    """
    if largura is None:
        largura = A4[0] - 4*cm
    
    drawing = Drawing(largura, 0.1*cm)
    line = Line(0, 0, largura, 0, strokeColor=CORES['borda'], strokeWidth=1)
    drawing.add(line)
    
    return drawing


def criar_resumo_executivo(dados_resumo):
    """
    Cria seção de resumo executivo com cards de métricas
    """
    elements = []
    
    # Título
    elements.append(criar_secao_titulo("📊 Resumo Executivo", nivel=1))
    elements.append(Spacer(1, 8))
    
    # Grid de cards (3 por linha para melhor aproveitamento)
    cards_data = []
    row = []
    
    for metrica in dados_resumo:
        titulo = metrica.get('titulo', '')
        valor = metrica.get('valor', '')
        cor = CORES.get(metrica.get('cor', 'primaria'), CORES['primaria'])
        
        card = criar_card_metrica(titulo, valor, cor, largura=5*cm, altura=2.5*cm)
        row.append(card)
        
        if len(row) == 3:  # 3 cards por linha
            cards_data.append(row)
            row = []
    
    # Adicionar última linha se houver
    if row:
        # Preencher com espaços vazios para alinhar
        while len(row) < 3:
            row.append(Spacer(5*cm, 2.5*cm))
        cards_data.append(row)
    
    # Criar tabela de cards com espaçamento reduzido
    if cards_data:
        cards_table = Table(cards_data, colWidths=[5.2*cm, 5.2*cm, 5.2*cm], spaceBefore=5, spaceAfter=15)
        cards_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(cards_table)
    
    return elements


def criar_grafico_barras(dados, titulo, largura=15*cm, altura=8*cm):
    """
    Cria gráfico de barras profissional
    """
    drawing = Drawing(largura, altura)
    
    chart = VerticalBarChart()
    chart.x = 1*cm
    chart.y = 1*cm
    chart.width = largura - 2*cm
    chart.height = altura - 3*cm
    
    # Dados
    chart.data = [dados.get('valores', [])]
    chart.categoryAxis.categoryNames = dados.get('categorias', [])
    
    # Cores
    chart.bars[0].fillColor = CORES['secundaria']
    chart.bars[0].strokeColor = CORES['primaria']
    chart.bars[0].strokeWidth = 1
    
    # Eixos
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueStep = dados.get('step', 10)
    chart.categoryAxis.labels.angle = 45
    chart.categoryAxis.labels.fontSize = 8
    chart.valueAxis.labels.fontSize = 8
    
    drawing.add(chart)
    
    # Título do gráfico
    titulo_grafico = String(largura/2, altura - 0.5*cm, titulo,
                           fontSize=12, fillColor=CORES['primaria'], 
                           textAnchor='middle', fontName='Helvetica-Bold')
    drawing.add(titulo_grafico)
    
    return drawing


def gerar_pdf_profissional(titulo, periodo, dados, tipo_relatorio, dados_resumo=None):
    """
    Função principal para gerar PDF com template profissional
    """
    buffer = BytesIO()
    
    # Configurar documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=3*cm,
        bottomMargin=2.5*cm,
        title=titulo,
        author="Kredor"
    )
    
    # Elementos do documento
    elements = []
    
    # Resumo executivo (se houver) - direto na primeira página
    if dados_resumo:
        elements.extend(criar_resumo_executivo(dados_resumo))
        elements.append(Spacer(1, 15))
    
    # Título da seção de dados
    elements.append(criar_secao_titulo(f"📋 Dados Detalhados - {tipo_relatorio.title()}", nivel=1))
    elements.append(Spacer(1, 10))
    
    # Tabela de dados
    if dados:
        tabela = criar_tabela_profissional(dados)
        elements.append(tabela)
    else:
        elements.append(criar_paragrafo("Nenhum dado encontrado para o período selecionado.", 'nota'))
    
    elements.append(Spacer(1, 20))
    elements.append(criar_linha_separadora())
    elements.append(Spacer(1, 10))
    
    # Nota de rodapé
    nota = """
    <b>Nota:</b> Este relatório foi gerado automaticamente pelo sistema Kredor. 
    Todas as informações são confidenciais e destinadas exclusivamente ao uso interno.
    Para dúvidas ou suporte, entre em contato com nossa equipe.
    """
    elements.append(criar_paragrafo(nota, 'nota'))
    
    # Construir PDF com cabeçalho e rodapé personalizados em todas as páginas
    def todas_paginas(canvas, doc):
        canvas.saveState()
        criar_cabecalho(canvas, doc, titulo, periodo)
        criar_rodape(canvas, doc)
        canvas.restoreState()
    
    doc.build(elements, onFirstPage=todas_paginas, onLaterPages=todas_paginas)
    
    buffer.seek(0)
    return buffer
