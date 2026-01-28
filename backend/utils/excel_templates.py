"""
Templates profissionais para relatórios Excel
Design moderno com formatação avançada e gráficos
"""
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, PieChart, LineChart, Reference
from openpyxl.drawing.image import Image as XLImage
from datetime import datetime
from io import BytesIO


# Paleta de cores profissional
CORES_EXCEL = {
    'primaria': '1E40AF',       # Azul escuro
    'secundaria': '3B82F6',     # Azul médio
    'acento': '60A5FA',         # Azul claro
    'sucesso': '10B981',        # Verde
    'alerta': 'F59E0B',         # Laranja
    'erro': 'EF4444',           # Vermelho
    'texto': '1F2937',          # Cinza escuro
    'texto_claro': '6B7280',    # Cinza médio
    'fundo': 'F9FAFB',          # Cinza muito claro
    'borda': 'E5E7EB',          # Cinza claro
}


def criar_estilos_excel():
    """
    Cria estilos nomeados reutilizáveis
    """
    # Estilo de cabeçalho
    cabecalho_style = NamedStyle(name="cabecalho")
    cabecalho_style.font = Font(
        name='Calibri',
        size=12,
        bold=True,
        color='FFFFFF'
    )
    cabecalho_style.fill = PatternFill(
        start_color=CORES_EXCEL['primaria'],
        end_color=CORES_EXCEL['primaria'],
        fill_type='solid'
    )
    cabecalho_style.alignment = Alignment(
        horizontal='center',
        vertical='center',
        wrap_text=True
    )
    cabecalho_style.border = Border(
        left=Side(style='thin', color=CORES_EXCEL['borda']),
        right=Side(style='thin', color=CORES_EXCEL['borda']),
        top=Side(style='thin', color=CORES_EXCEL['borda']),
        bottom=Side(style='medium', color=CORES_EXCEL['primaria'])
    )
    
    # Estilo de célula normal
    celula_style = NamedStyle(name="celula")
    celula_style.font = Font(name='Calibri', size=10)
    celula_style.alignment = Alignment(horizontal='left', vertical='center')
    celula_style.border = Border(
        left=Side(style='thin', color=CORES_EXCEL['borda']),
        right=Side(style='thin', color=CORES_EXCEL['borda']),
        top=Side(style='thin', color=CORES_EXCEL['borda']),
        bottom=Side(style='thin', color=CORES_EXCEL['borda'])
    )
    
    # Estilo de célula alternada
    celula_alt_style = NamedStyle(name="celula_alt")
    celula_alt_style.font = Font(name='Calibri', size=10)
    celula_alt_style.fill = PatternFill(
        start_color=CORES_EXCEL['fundo'],
        end_color=CORES_EXCEL['fundo'],
        fill_type='solid'
    )
    celula_alt_style.alignment = Alignment(horizontal='left', vertical='center')
    celula_alt_style.border = Border(
        left=Side(style='thin', color=CORES_EXCEL['borda']),
        right=Side(style='thin', color=CORES_EXCEL['borda']),
        top=Side(style='thin', color=CORES_EXCEL['borda']),
        bottom=Side(style='thin', color=CORES_EXCEL['borda'])
    )
    
    # Estilo de título
    titulo_style = NamedStyle(name="titulo")
    titulo_style.font = Font(
        name='Calibri',
        size=18,
        bold=True,
        color=CORES_EXCEL['primaria']
    )
    titulo_style.alignment = Alignment(horizontal='left', vertical='center')
    
    # Estilo de subtítulo
    subtitulo_style = NamedStyle(name="subtitulo")
    subtitulo_style.font = Font(
        name='Calibri',
        size=11,
        color=CORES_EXCEL['texto_claro']
    )
    subtitulo_style.alignment = Alignment(horizontal='left', vertical='center')
    
    # Estilo de métrica (card)
    metrica_style = NamedStyle(name="metrica")
    metrica_style.font = Font(
        name='Calibri',
        size=24,
        bold=True,
        color='FFFFFF'
    )
    metrica_style.fill = PatternFill(
        start_color=CORES_EXCEL['primaria'],
        end_color=CORES_EXCEL['primaria'],
        fill_type='solid'
    )
    metrica_style.alignment = Alignment(horizontal='center', vertical='center')
    
    return {
        'cabecalho': cabecalho_style,
        'celula': celula_style,
        'celula_alt': celula_alt_style,
        'titulo': titulo_style,
        'subtitulo': subtitulo_style,
        'metrica': metrica_style,
    }


def adicionar_cabecalho_excel(ws, titulo, periodo, linha_inicial=1):
    """
    Adiciona cabeçalho profissional na planilha
    """
    # Título do relatório
    ws.merge_cells(f'A{linha_inicial}:F{linha_inicial}')
    cell = ws[f'A{linha_inicial}']
    cell.value = titulo
    cell.font = Font(name='Calibri', size=18, bold=True, color=CORES_EXCEL['primaria'])
    cell.alignment = Alignment(horizontal='left', vertical='center')
    
    # Empresa
    ws.merge_cells(f'G{linha_inicial}:I{linha_inicial}')
    cell = ws[f'G{linha_inicial}']
    cell.value = "Gestor Cred"
    cell.font = Font(name='Calibri', size=14, bold=True, color=CORES_EXCEL['secundaria'])
    cell.alignment = Alignment(horizontal='right', vertical='center')
    
    # Período
    linha_inicial += 1
    ws.merge_cells(f'A{linha_inicial}:F{linha_inicial}')
    cell = ws[f'A{linha_inicial}']
    cell.value = f"Período: {periodo}"
    cell.font = Font(name='Calibri', size=11, color=CORES_EXCEL['texto_claro'])
    cell.alignment = Alignment(horizontal='left', vertical='center')
    
    # Data de geração
    ws.merge_cells(f'G{linha_inicial}:I{linha_inicial}')
    cell = ws[f'G{linha_inicial}']
    data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M")
    cell.value = f"Gerado em: {data_geracao}"
    cell.font = Font(name='Calibri', size=9, color=CORES_EXCEL['texto_claro'])
    cell.alignment = Alignment(horizontal='right', vertical='center')
    
    return linha_inicial + 2  # Retorna próxima linha disponível


def adicionar_secao_resumo(ws, dados_resumo, linha_inicial):
    """
    Adiciona seção de resumo com cards de métricas
    """
    # Título da seção
    ws.merge_cells(f'A{linha_inicial}:I{linha_inicial}')
    cell = ws[f'A{linha_inicial}']
    cell.value = "📊 RESUMO EXECUTIVO"
    cell.font = Font(name='Calibri', size=14, bold=True, color=CORES_EXCEL['primaria'])
    cell.alignment = Alignment(horizontal='left', vertical='center')
    
    linha_inicial += 2
    
    # Cards de métricas (3 por linha) - SEM células mescladas para evitar erros
    col_offset = 0
    for idx, metrica in enumerate(dados_resumo):
        if idx > 0 and idx % 3 == 0:
            linha_inicial += 3
            col_offset = 0
        
        # Calcular coluna inicial do card
        col_inicio = col_offset * 3 + 1  # A=1, D=4, G=7
        col_fim = col_inicio + 2
        
        cor_card = CORES_EXCEL.get(metrica.get('cor', 'primaria'), CORES_EXCEL['primaria'])
        
        # Criar card em 3 linhas separadas (sem merge)
        # Linha 1: Título
        for col in range(col_inicio, col_fim + 1):
            cell = ws.cell(row=linha_inicial, column=col)
            if col == col_inicio:
                cell.value = metrica.get('titulo', '')
            cell.fill = PatternFill(start_color=cor_card, end_color=cor_card, fill_type='solid')
            cell.font = Font(name='Calibri', size=10, color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = Border(
                left=Side(style='thin', color='FFFFFF'),
                right=Side(style='thin', color='FFFFFF'),
                top=Side(style='medium', color='FFFFFF'),
                bottom=Side(style='thin', color='FFFFFF')
            )
        
        # Linha 2: Valor
        for col in range(col_inicio, col_fim + 1):
            cell = ws.cell(row=linha_inicial + 1, column=col)
            if col == col_inicio:
                cell.value = metrica.get('valor', '')
            cell.fill = PatternFill(start_color=cor_card, end_color=cor_card, fill_type='solid')
            cell.font = Font(name='Calibri', size=16, color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = Border(
                left=Side(style='thin', color='FFFFFF'),
                right=Side(style='thin', color='FFFFFF'),
                top=Side(style='thin', color='FFFFFF'),
                bottom=Side(style='medium', color='FFFFFF')
            )
        
        col_offset += 1
    
    return linha_inicial + 4


def adicionar_tabela_dados(ws, dados, headers, linha_inicial):
    """
    Adiciona tabela de dados com formatação profissional
    """
    # Título da seção
    ws.merge_cells(f'A{linha_inicial}:I{linha_inicial}')
    cell = ws[f'A{linha_inicial}']
    cell.value = "📋 DADOS DETALHADOS"
    cell.font = Font(name='Calibri', size=14, bold=True, color=CORES_EXCEL['primaria'])
    cell.alignment = Alignment(horizontal='left', vertical='center')
    
    linha_inicial += 2
    
    # Cabeçalhos
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=linha_inicial, column=col_idx, value=header)
        cell.font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        cell.fill = PatternFill(
            start_color=CORES_EXCEL['primaria'],
            end_color=CORES_EXCEL['primaria'],
            fill_type='solid'
        )
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = Border(
            left=Side(style='thin', color=CORES_EXCEL['borda']),
            right=Side(style='thin', color=CORES_EXCEL['borda']),
            top=Side(style='thin', color=CORES_EXCEL['borda']),
            bottom=Side(style='medium', color=CORES_EXCEL['primaria'])
        )
        
        # Ajustar largura da coluna
        ws.column_dimensions[get_column_letter(col_idx)].width = 18
    
    linha_inicial += 1
    
    # Dados
    for row_idx, row_data in enumerate(dados):
        for col_idx, header in enumerate(headers, 1):
            valor = row_data.get(header, "") if isinstance(row_data, dict) else row_data[col_idx - 1]
            cell = ws.cell(row=linha_inicial + row_idx, column=col_idx, value=valor)
            
            # Alternar cores de fundo
            if row_idx % 2 == 0:
                cell.fill = PatternFill(
                    start_color='FFFFFF',
                    end_color='FFFFFF',
                    fill_type='solid'
                )
            else:
                cell.fill = PatternFill(
                    start_color=CORES_EXCEL['fundo'],
                    end_color=CORES_EXCEL['fundo'],
                    fill_type='solid'
                )
            
            cell.font = Font(name='Calibri', size=10, color=CORES_EXCEL['texto'])
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = Border(
                left=Side(style='thin', color=CORES_EXCEL['borda']),
                right=Side(style='thin', color=CORES_EXCEL['borda']),
                top=Side(style='thin', color=CORES_EXCEL['borda']),
                bottom=Side(style='thin', color=CORES_EXCEL['borda'])
            )
    
    return linha_inicial + len(dados) + 2


def adicionar_rodape_excel(ws, linha_final):
    """
    Adiciona rodapé com informações da empresa
    """
    linha_final += 2
    
    ws.merge_cells(f'A{linha_final}:I{linha_final}')
    cell = ws[f'A{linha_final}']
    cell.value = "Gestor Cred - Sistema de Gestão de Empréstimos | www.jurofacil.com.br | Confidencial"
    cell.font = Font(name='Calibri', size=8, color=CORES_EXCEL['texto_claro'], italic=True)
    cell.alignment = Alignment(horizontal='center', vertical='center')
    
    return linha_final


def gerar_excel_profissional(titulo, periodo, dados, tipo_relatorio, dados_resumo=None):
    """
    Função principal para gerar Excel com template profissional
    """
    wb = Workbook()
    ws = wb.active
    ws.title = tipo_relatorio.capitalize()[:31]  # Limite de 31 caracteres para nome de aba
    
    # Configurar página
    ws.sheet_properties.tabColor = CORES_EXCEL['primaria']
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = 9  # A4
    
    # Adicionar cabeçalho
    linha_atual = adicionar_cabecalho_excel(ws, titulo, periodo)
    
    # Adicionar resumo executivo (se houver)
    if dados_resumo and len(dados_resumo) > 0:
        linha_atual = adicionar_secao_resumo(ws, dados_resumo, linha_atual)
    
    # Adicionar tabela de dados
    if dados and len(dados) > 0:
        headers = list(dados[0].keys()) if isinstance(dados[0], dict) else [f"Coluna {i+1}" for i in range(len(dados[0]))]
        linha_atual = adicionar_tabela_dados(ws, dados, headers, linha_atual)
    
    # Adicionar rodapé
    adicionar_rodape_excel(ws, linha_atual)
    
    # Ajustar zoom
    ws.sheet_view.zoomScale = 90
    
    # Congelar primeira linha de cabeçalho (ajustar conforme a linha dos dados)
    ws.freeze_panes = 'A7'
    
    # Salvar em buffer
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    return buffer
