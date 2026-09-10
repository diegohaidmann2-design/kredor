"""
Rotas de Contratos
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

from config import db
from models.contrato import ContratoRequest
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context, is_owner
from services.permissao_service import verificar_recurso
from utils.dinheiro import formatar_reais, arredondar_centavos
from services.permissao_service import permissao_service

router = APIRouter()


def numero_por_extenso(valor_centavos: int) -> str:
    """Converte um valor em centavos para extenso (simplificado)"""
    inteiro, centavos = divmod(int(valor_centavos or 0), 100)
    
    unidades = ["", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"]
    dezenas = ["", "dez", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
    centenas = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"]
    especiais = {11: "onze", 12: "doze", 13: "treze", 14: "quatorze", 15: "quinze", 16: "dezesseis", 17: "dezessete", 18: "dezoito", 19: "dezenove"}
    
    if inteiro == 0:
        return "zero reais"
    
    resultado = ""
    
    # Milhões
    if inteiro >= 1000000:
        milhoes = inteiro // 1000000
        resto = inteiro % 1000000
        if milhoes == 1:
            resultado = "um milhão"
        else:
            resultado = f"{unidades[milhoes]} milhões"
        inteiro = resto
        if inteiro > 0:
            resultado += " e " if inteiro < 1000 else ", "
    
    # Milhares
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
            dezena = milhares // 10
            unidade = milhares % 10
            resultado += dezenas[dezena]
            if unidade > 0:
                resultado += f" e {unidades[unidade]}"
            resultado += " mil"
        else:
            centena = milhares // 100
            resto_mil = milhares % 100
            if milhares == 100:
                resultado += "cem mil"
            else:
                resultado += centenas[centena]
                if resto_mil > 0:
                    if resto_mil in especiais:
                        resultado += f" e {especiais[resto_mil]}"
                    elif resto_mil < 10:
                        resultado += f" e {unidades[resto_mil]}"
                    else:
                        dezena = resto_mil // 10
                        unidade = resto_mil % 10
                        resultado += f" e {dezenas[dezena]}"
                        if unidade > 0:
                            resultado += f" e {unidades[unidade]}"
                resultado += " mil"
        inteiro = resto
        if inteiro > 0:
            resultado += " e " if inteiro < 100 else ", "
    
    # Centenas
    if inteiro >= 100:
        if inteiro == 100:
            resultado += "cem"
        else:
            resultado += centenas[inteiro // 100]
            inteiro = inteiro % 100
            if inteiro > 0:
                resultado += " e "
    
    # Dezenas e unidades
    if inteiro >= 10:
        if inteiro in especiais:
            resultado += especiais[inteiro]
            inteiro = 0
        else:
            resultado += dezenas[inteiro // 10]
            inteiro = inteiro % 10
            if inteiro > 0:
                resultado += " e "
    
    if inteiro > 0:
        resultado += unidades[inteiro]
    
    resultado += " reais"
    
    if centavos > 0:
        if centavos == 1:
            resultado += " e um centavo"
        else:
            resultado += f" e {centavos} centavos"
    
    return resultado


def gerar_contrato_padrao(elements, styles, emprestimo, cliente, parcelas, credor_nome):
    """Gera contrato no template padrão"""
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=20)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=12, alignment=TA_CENTER, spaceAfter=10)
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=11, spaceAfter=10, alignment=TA_JUSTIFY)
    clause_style = ParagraphStyle('Clause', parent=styles['Heading3'], fontSize=12, spaceBefore=15, spaceAfter=8, textColor=colors.HexColor('#1a365d'))
    
    elements.append(Paragraph("CONTRATO DE EMPRÉSTIMO", title_style))
    elements.append(Paragraph("Instrumento Particular de Mútuo", subtitle_style))
    elements.append(Spacer(1, 20))
    
    data_hoje = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    valor_extenso = numero_por_extenso(emprestimo["valor_principal_centavos"])
    
    # Identificação das partes
    elements.append(Paragraph("<b>IDENTIFICAÇÃO DAS PARTES</b>", clause_style))
    
    texto_partes = f"""
    <b>CREDOR (MUTUANTE):</b> {credor_nome}<br/><br/>
    <b>DEVEDOR (MUTUÁRIO):</b><br/>
    Nome: {cliente['nome']}<br/>
    CPF/CNPJ: {cliente['cpf_cnpj']}<br/>
    Telefone: {cliente.get('telefone', 'Não informado')}<br/>
    Email: {cliente.get('email', 'Não informado')}<br/>
    Endereço: {cliente['endereco']['rua']}, {cliente['endereco']['numero']} 
    {f"- {cliente['endereco'].get('complemento')}" if cliente['endereco'].get('complemento') else ''}<br/>
    Bairro: {cliente['endereco']['bairro']}<br/>
    Cidade/UF: {cliente['endereco']['cidade']}/{cliente['endereco']['estado']} - CEP: {cliente['endereco']['cep']}<br/>
    """
    elements.append(Paragraph(texto_partes, normal_style))
    elements.append(Spacer(1, 10))
    
    # Cláusula Primeira - Do Objeto
    elements.append(Paragraph("CLÁUSULA PRIMEIRA - DO OBJETO", clause_style))
    texto_objeto = f"""
    O presente contrato tem por objeto o empréstimo pessoal (mútuo) da quantia de 
    <b>R$ {formatar_reais(emprestimo['valor_principal_centavos'])}</b> ({valor_extenso}), que o CREDOR concede ao DEVEDOR nesta data,
    mediante as condições estabelecidas nas cláusulas seguintes.
    """
    elements.append(Paragraph(texto_objeto, normal_style))
    
    # Cláusula Segunda - Dos Juros e Encargos
    elements.append(Paragraph("CLÁUSULA SEGUNDA - DOS JUROS E ENCARGOS", clause_style))
    metodo_nome = {
        'simples': 'Juros Simples',
        'composto': 'Juros Compostos',
        'price': 'Tabela Price',
        'sac': 'Sistema de Amortização Constante (SAC)'
    }.get(emprestimo['metodo_calculo'], emprestimo['metodo_calculo'])
    
    texto_juros = f"""
    2.1. O valor emprestado será acrescido de juros remuneratórios à taxa de <b>{emprestimo['taxa_juros_mensal']}% ao mês</b>.<br/><br/>
    2.2. O método de cálculo utilizado será o <b>{metodo_nome}</b>.<br/><br/>
    2.3. O valor total a ser pago, incluindo principal e juros, será de <b>R$ {formatar_reais(emprestimo['valor_total_com_juros_centavos'])}</b>.
    """
    elements.append(Paragraph(texto_juros, normal_style))
    
    # Calcular valor da parcela se não existir (robustez)
    valor_parcela = emprestimo.get('valor_parcela')
    if not valor_parcela:
        valor_parcela = arredondar_centavos(emprestimo.get('valor_total_com_juros_centavos', 0) / max(emprestimo.get('prazo_meses', 1), 1))
    
    # Data primeiro vencimento com fallback
    data_venc = emprestimo.get('data_primeiro_vencimento', 'Conforme acordado')
    if hasattr(data_venc, 'strftime'):
        data_venc = data_venc.strftime('%d/%m/%Y')
    elif isinstance(data_venc, str) and 'T' in data_venc:
        data_venc = data_venc.split('T')[0]
    
    # Cláusula Terceira - Do Pagamento
    elements.append(Paragraph("CLÁUSULA TERCEIRA - DO PAGAMENTO", clause_style))
    texto_pagamento = f"""
    3.1. O DEVEDOR pagará ao CREDOR o valor total em <b>{emprestimo.get('prazo_meses', 1)} parcelas</b> mensais e consecutivas,
    no valor aproximado de <b>R$ {formatar_reais(valor_parcela)}</b> cada.<br/><br/>
    3.2. O vencimento da primeira parcela será em <b>{data_venc}</b>.<br/><br/>
    3.3. Os pagamentos deverão ser realizados até a data de vencimento de cada parcela.
    """
    elements.append(Paragraph(texto_pagamento, normal_style))
    
    # Cláusula Quarta - Da Mora
    elements.append(Paragraph("CLÁUSULA QUARTA - DA MORA E INADIMPLÊNCIA", clause_style))
    texto_mora = f"""
    4.1. Em caso de atraso no pagamento, incidirá multa de <b>{emprestimo.get('taxa_multa_atraso', 2)}%</b> sobre o valor da parcela.<br/><br/>
    4.2. Além da multa, serão cobrados juros de mora de <b>{emprestimo.get('taxa_juros_mora_diario', 0.033)}% ao dia</b>.<br/><br/>
    4.3. O não pagamento de qualquer parcela por prazo superior a 30 (trinta) dias importará no vencimento 
    antecipado de todas as parcelas vincendas, tornando-se exigível a totalidade do débito.
    """
    elements.append(Paragraph(texto_mora, normal_style))
    
    # Cláusula Quinta - Das Disposições Gerais
    elements.append(Paragraph("CLÁUSULA QUINTA - DAS DISPOSIÇÕES GERAIS", clause_style))
    texto_disposicoes = f"""
    5.1. O presente contrato obriga as partes e seus sucessores.<br/><br/>
    5.2. Qualquer tolerância do CREDOR não importará em novação ou renúncia de direitos.<br/><br/>
    5.3. As partes declaram que o presente instrumento é celebrado de boa-fé e livre de vícios.
    """
    elements.append(Paragraph(texto_disposicoes, normal_style))
    
    # Cláusula Sexta - Do Foro
    elements.append(Paragraph("CLÁUSULA SEXTA - DO FORO", clause_style))
    texto_foro = f"""
    As partes elegem o foro da comarca de <b>{cliente['endereco']['cidade']}/{cliente['endereco']['estado']}</b> 
    para dirimir quaisquer dúvidas ou litígios oriundos do presente contrato, com renúncia expressa a qualquer outro,
    por mais privilegiado que seja.
    """
    elements.append(Paragraph(texto_foro, normal_style))
    
    # Assinaturas
    elements.append(Spacer(1, 30))
    texto_encerramento = f"""
    E, por estarem assim justos e contratados, as partes firmam o presente instrumento em 02 (duas) vias de igual 
    teor e forma, na presença de 02 (duas) testemunhas, para que produza seus efeitos legais.<br/><br/>
    <b>{cliente['endereco']['cidade']}/{cliente['endereco']['estado']}, {data_hoje}</b>
    """
    elements.append(Paragraph(texto_encerramento, normal_style))
    
    elements.append(Spacer(1, 40))
    
    assinaturas = """
    <br/><br/>
    _____________________________________________<br/>
    <b>CREDOR</b><br/><br/><br/><br/>
    
    _____________________________________________<br/>
    <b>DEVEDOR</b><br/><br/><br/><br/>
    
    <b>TESTEMUNHAS:</b><br/><br/>
    1. ___________________________________ CPF: ___________________<br/><br/>
    2. ___________________________________ CPF: ___________________
    """
    elements.append(Paragraph(assinaturas, normal_style))
    
    # Tabela de Parcelas (nova página)
    if parcelas:
        elements.append(PageBreak())
        elements.append(Paragraph("ANEXO I - TABELA DE PARCELAS", title_style))
        elements.append(Spacer(1, 20))
        
        # Criar tabela
        table_data = [["Nº", "Vencimento", "Valor", "Status"]]
        for p in parcelas:
            # Status robusto - verifica 'pago', 'status' ou valor_pago_centavos
            status_val = p.get('status', '')
            is_pago = p.get('pago') or status_val == 'pago' or (p.get('valor_pago_centavos', 0) > 0)
            status = "Pago" if is_pago else "Pendente"
            
            # Data vencimento formatada
            data_venc = p.get('data_vencimento', '')
            if hasattr(data_venc, 'strftime'):
                data_venc = data_venc.strftime('%d/%m/%Y')
            elif isinstance(data_venc, str) and 'T' in data_venc:
                data_venc = data_venc.split('T')[0]
            
            table_data.append([
                str(p.get('numero_parcela', '?')),
                data_venc,
                f"R$ {formatar_reais(p.get('valor_total_centavos', p.get('valor', 0)))}",
                status
            ])
        
        table = Table(table_data, colWidths=[2*cm, 4*cm, 4*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ]))
        elements.append(table)


def gerar_contrato_garantia(elements, styles, emprestimo, cliente, parcelas, credor_nome):
    """Gera contrato com cláusulas de garantia"""
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=20)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=12, alignment=TA_CENTER, spaceAfter=10)
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=11, spaceAfter=10, alignment=TA_JUSTIFY)
    clause_style = ParagraphStyle('Clause', parent=styles['Heading3'], fontSize=12, spaceBefore=15, spaceAfter=8, textColor=colors.HexColor('#1a365d'))
    
    elements.append(Paragraph("CONTRATO DE EMPRÉSTIMO COM GARANTIA", title_style))
    elements.append(Paragraph("Instrumento Particular de Mútuo com Cláusula de Garantia", subtitle_style))
    elements.append(Spacer(1, 20))
    
    data_hoje = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    valor_extenso = numero_por_extenso(emprestimo["valor_principal_centavos"])
    
    # Identificação das partes
    elements.append(Paragraph("<b>IDENTIFICAÇÃO DAS PARTES</b>", clause_style))
    
    texto_partes = f"""
    <b>CREDOR (MUTUANTE):</b> {credor_nome}<br/><br/>
    <b>DEVEDOR (MUTUÁRIO):</b><br/>
    Nome: {cliente['nome']}<br/>
    CPF/CNPJ: {cliente['cpf_cnpj']}<br/>
    Telefone: {cliente.get('telefone', 'Não informado')}<br/>
    Email: {cliente.get('email', 'Não informado')}<br/>
    Endereço: {cliente['endereco']['rua']}, {cliente['endereco']['numero']} 
    {f"- {cliente['endereco'].get('complemento')}" if cliente['endereco'].get('complemento') else ''}<br/>
    Bairro: {cliente['endereco']['bairro']}<br/>
    Cidade/UF: {cliente['endereco']['cidade']}/{cliente['endereco']['estado']} - CEP: {cliente['endereco']['cep']}<br/>
    """
    elements.append(Paragraph(texto_partes, normal_style))
    elements.append(Spacer(1, 10))
    
    # Cláusula Primeira - Do Objeto
    elements.append(Paragraph("CLÁUSULA PRIMEIRA - DO OBJETO", clause_style))
    texto_objeto = f"""
    O presente contrato tem por objeto o empréstimo pessoal (mútuo) da quantia de 
    <b>R$ {formatar_reais(emprestimo['valor_principal_centavos'])}</b> ({valor_extenso}), que o CREDOR concede ao DEVEDOR nesta data,
    mediante as condições estabelecidas nas cláusulas seguintes e com a garantia especificada na Cláusula Sétima.
    """
    elements.append(Paragraph(texto_objeto, normal_style))
    
    # Cláusula Segunda - Dos Juros e Encargos
    elements.append(Paragraph("CLÁUSULA SEGUNDA - DOS JUROS E ENCARGOS", clause_style))
    metodo_nome = {
        'simples': 'Juros Simples',
        'composto': 'Juros Compostos',
        'price': 'Tabela Price',
        'sac': 'Sistema de Amortização Constante (SAC)'
    }.get(emprestimo['metodo_calculo'], emprestimo['metodo_calculo'])
    
    texto_juros = f"""
    2.1. O valor emprestado será acrescido de juros remuneratórios à taxa de <b>{emprestimo['taxa_juros_mensal']}% ao mês</b>.<br/><br/>
    2.2. O método de cálculo utilizado será o <b>{metodo_nome}</b>.<br/><br/>
    2.3. O valor total a ser pago, incluindo principal e juros, será de <b>R$ {formatar_reais(emprestimo['valor_total_com_juros_centavos'])}</b>.
    """
    elements.append(Paragraph(texto_juros, normal_style))
    
    # Calcular valor da parcela se não existir (robustez)
    valor_parcela = emprestimo.get('valor_parcela')
    if not valor_parcela:
        valor_parcela = arredondar_centavos(emprestimo.get('valor_total_com_juros_centavos', 0) / max(emprestimo.get('prazo_meses', 1), 1))
    
    # Data primeiro vencimento com fallback
    data_venc = emprestimo.get('data_primeiro_vencimento', 'Conforme acordado')
    if hasattr(data_venc, 'strftime'):
        data_venc = data_venc.strftime('%d/%m/%Y')
    elif isinstance(data_venc, str) and 'T' in data_venc:
        data_venc = data_venc.split('T')[0]
    
    # Cláusula Terceira - Do Pagamento
    elements.append(Paragraph("CLÁUSULA TERCEIRA - DO PAGAMENTO", clause_style))
    texto_pagamento = f"""
    3.1. O DEVEDOR pagará ao CREDOR o valor total em <b>{emprestimo.get('prazo_meses', 1)} parcelas</b> mensais e consecutivas,
    no valor aproximado de <b>R$ {formatar_reais(valor_parcela)}</b> cada.<br/><br/>
    3.2. O vencimento da primeira parcela será em <b>{data_venc}</b>.<br/><br/>
    3.3. Os pagamentos deverão ser realizados até a data de vencimento de cada parcela.
    """
    elements.append(Paragraph(texto_pagamento, normal_style))
    
    # Cláusula Quarta - Da Mora
    elements.append(Paragraph("CLÁUSULA QUARTA - DA MORA E INADIMPLÊNCIA", clause_style))
    texto_mora = f"""
    4.1. Em caso de atraso no pagamento, incidirá multa de <b>{emprestimo.get('taxa_multa_atraso', 2)}%</b> sobre o valor da parcela.<br/><br/>
    4.2. Além da multa, serão cobrados juros de mora de <b>{emprestimo.get('taxa_juros_mora_diario', 0.033)}% ao dia</b>.<br/><br/>
    4.3. O não pagamento de qualquer parcela por prazo superior a 30 (trinta) dias importará no vencimento 
    antecipado de todas as parcelas vincendas, tornando-se exigível a totalidade do débito, podendo o CREDOR
    executar a garantia prevista na Cláusula Sétima.
    """
    elements.append(Paragraph(texto_mora, normal_style))
    
    # Cláusula Quinta - Das Disposições Gerais
    elements.append(Paragraph("CLÁUSULA QUINTA - DAS DISPOSIÇÕES GERAIS", clause_style))
    texto_disposicoes = f"""
    5.1. O presente contrato obriga as partes e seus sucessores.<br/><br/>
    5.2. Qualquer tolerância do CREDOR não importará em novação ou renúncia de direitos.<br/><br/>
    5.3. As partes declaram que o presente instrumento é celebrado de boa-fé e livre de vícios.
    """
    elements.append(Paragraph(texto_disposicoes, normal_style))
    
    # Cláusula Sexta - Do Foro
    elements.append(Paragraph("CLÁUSULA SEXTA - DO FORO", clause_style))
    texto_foro = f"""
    As partes elegem o foro da comarca de <b>{cliente['endereco']['cidade']}/{cliente['endereco']['estado']}</b> 
    para dirimir quaisquer dúvidas ou litígios oriundos do presente contrato, com renúncia expressa a qualquer outro,
    por mais privilegiado que seja.
    """
    elements.append(Paragraph(texto_foro, normal_style))
    
    # Cláusula Sétima - Da Garantia (ESPECÍFICA DESTE TEMPLATE)
    elements.append(Paragraph("CLÁUSULA SÉTIMA - DA GARANTIA", clause_style))
    texto_garantia = f"""
    7.1. Como garantia do fiel cumprimento das obrigações assumidas neste contrato, o DEVEDOR oferece em garantia:
    <br/><br/>
    <b>DESCRIÇÃO DA GARANTIA:</b> ________________________________________________<br/>
    _________________________________________________________________________<br/>
    _________________________________________________________________________<br/><br/>
    
    7.2. O DEVEDOR declara ser o legítimo proprietário do bem dado em garantia, livre e desembaraçado de quaisquer 
    ônus, dívidas ou pendências judiciais ou extrajudiciais.<br/><br/>
    
    7.3. O DEVEDOR compromete-se a manter o bem em perfeito estado de conservação durante a vigência deste contrato,
    não podendo aliená-lo, cedê-lo ou transferi-lo a terceiros sem a prévia e expressa autorização do CREDOR.<br/><br/>
    
    7.4. Em caso de inadimplemento, o CREDOR poderá:<br/>
    a) Executar judicialmente a garantia oferecida;<br/>
    b) Tomar posse do bem dado em garantia;<br/>
    c) Alienar o bem para satisfação do crédito, aplicando o valor obtido na quitação do débito.<br/><br/>
    
    7.5. Caso o valor obtido com a alienação da garantia seja insuficiente para quitar o débito, o DEVEDOR permanecerá
    responsável pelo saldo remanescente.<br/><br/>
    
    7.6. Caso o valor obtido seja superior ao débito, a diferença será devolvida ao DEVEDOR em até 10 (dez) dias úteis.
    """
    elements.append(Paragraph(texto_garantia, normal_style))
    
    # Cláusula Oitava - Da Execução da Garantia
    elements.append(Paragraph("CLÁUSULA OITAVA - DA EXECUÇÃO DA GARANTIA", clause_style))
    texto_execucao = f"""
    8.1. A execução da garantia poderá ocorrer nas seguintes hipóteses:<br/>
    a) Atraso superior a 30 (trinta) dias no pagamento de qualquer parcela;<br/>
    b) Deterioração ou perecimento do bem dado em garantia por culpa do DEVEDOR;<br/>
    c) Transferência ou alienação do bem sem autorização do CREDOR;<br/>
    d) Declaração de falência ou insolvência do DEVEDOR;<br/>
    e) Prestação de informações falsas pelo DEVEDOR.<br/><br/>
    
    8.2. Antes da execução, o CREDOR notificará o DEVEDOR, por escrito, concedendo prazo de 15 (quinze) dias
    para regularização da situação.<br/><br/>
    
    8.3. O DEVEDOR autoriza expressamente o CREDOR a tomar posse do bem dado em garantia, caso configurada
    qualquer das hipóteses previstas no item 8.1, após o decurso do prazo de regularização.
    """
    elements.append(Paragraph(texto_execucao, normal_style))
    
    # Assinaturas
    elements.append(Spacer(1, 30))
    texto_encerramento = f"""
    E, por estarem assim justos e contratados, as partes firmam o presente instrumento em 02 (duas) vias de igual 
    teor e forma, na presença de 02 (duas) testemunhas, para que produza seus efeitos legais.<br/><br/>
    <b>{cliente['endereco']['cidade']}/{cliente['endereco']['estado']}, {data_hoje}</b>
    """
    elements.append(Paragraph(texto_encerramento, normal_style))
    
    elements.append(Spacer(1, 40))
    
    assinaturas = """
    <br/><br/>
    _____________________________________________<br/>
    <b>CREDOR</b><br/><br/><br/><br/>
    
    _____________________________________________<br/>
    <b>DEVEDOR</b><br/><br/><br/><br/>
    
    <b>TESTEMUNHAS:</b><br/><br/>
    1. ___________________________________ CPF: ___________________<br/><br/>
    2. ___________________________________ CPF: ___________________
    """
    elements.append(Paragraph(assinaturas, normal_style))
    
    # Tabela de Parcelas (nova página)
    if parcelas:
        elements.append(PageBreak())
        elements.append(Paragraph("ANEXO I - TABELA DE PARCELAS", title_style))
        elements.append(Spacer(1, 20))
        
        table_data = [["Nº", "Vencimento", "Valor", "Status"]]
        for p in parcelas:
            # Status robusto - verifica 'pago', 'status' ou valor_pago_centavos
            status_val = p.get('status', '')
            is_pago = p.get('pago') or status_val == 'pago' or (p.get('valor_pago_centavos', 0) > 0)
            status = "Pago" if is_pago else "Pendente"
            
            # Data vencimento formatada
            data_venc = p.get('data_vencimento', '')
            if hasattr(data_venc, 'strftime'):
                data_venc = data_venc.strftime('%d/%m/%Y')
            elif isinstance(data_venc, str) and 'T' in data_venc:
                data_venc = data_venc.split('T')[0]
            
            table_data.append([
                str(p.get('numero_parcela', '?')),
                data_venc,
                f"R$ {formatar_reais(p.get('valor_total_centavos', p.get('valor', 0)))}",
                status
            ])
        
        table = Table(table_data, colWidths=[2*cm, 4*cm, 4*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ]))
        elements.append(table)


def gerar_contrato_personalizado(elements, styles, emprestimo, cliente, parcelas, credor_nome, clausulas_adicionais=None):
    """Gera contrato personalizado com cláusulas adicionais"""
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=20)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=12, alignment=TA_CENTER, spaceAfter=10)
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=11, spaceAfter=10, alignment=TA_JUSTIFY)
    clause_style = ParagraphStyle('Clause', parent=styles['Heading3'], fontSize=12, spaceBefore=15, spaceAfter=8, textColor=colors.HexColor('#1a365d'))
    custom_style = ParagraphStyle('Custom', parent=styles['Normal'], fontSize=11, spaceAfter=10, alignment=TA_JUSTIFY, 
                                   backgroundColor=colors.HexColor('#f8f9fa'), borderPadding=10)
    
    elements.append(Paragraph("CONTRATO DE EMPRÉSTIMO PERSONALIZADO", title_style))
    elements.append(Paragraph("Instrumento Particular de Mútuo com Cláusulas Especiais", subtitle_style))
    elements.append(Spacer(1, 20))
    
    data_hoje = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    valor_extenso = numero_por_extenso(emprestimo["valor_principal_centavos"])
    
    # Identificação das partes
    elements.append(Paragraph("<b>IDENTIFICAÇÃO DAS PARTES</b>", clause_style))
    
    texto_partes = f"""
    <b>CREDOR (MUTUANTE):</b> {credor_nome}<br/><br/>
    <b>DEVEDOR (MUTUÁRIO):</b><br/>
    Nome: {cliente['nome']}<br/>
    CPF/CNPJ: {cliente['cpf_cnpj']}<br/>
    Telefone: {cliente.get('telefone', 'Não informado')}<br/>
    Email: {cliente.get('email', 'Não informado')}<br/>
    Endereço: {cliente['endereco']['rua']}, {cliente['endereco']['numero']} 
    {f"- {cliente['endereco'].get('complemento')}" if cliente['endereco'].get('complemento') else ''}<br/>
    Bairro: {cliente['endereco']['bairro']}<br/>
    Cidade/UF: {cliente['endereco']['cidade']}/{cliente['endereco']['estado']} - CEP: {cliente['endereco']['cep']}<br/>
    """
    elements.append(Paragraph(texto_partes, normal_style))
    elements.append(Spacer(1, 10))
    
    # Cláusula Primeira - Do Objeto
    elements.append(Paragraph("CLÁUSULA PRIMEIRA - DO OBJETO", clause_style))
    texto_objeto = f"""
    O presente contrato tem por objeto o empréstimo pessoal (mútuo) da quantia de 
    <b>R$ {formatar_reais(emprestimo['valor_principal_centavos'])}</b> ({valor_extenso}), que o CREDOR concede ao DEVEDOR nesta data,
    mediante as condições estabelecidas nas cláusulas seguintes.
    """
    elements.append(Paragraph(texto_objeto, normal_style))
    
    # Cláusula Segunda - Dos Juros e Encargos
    elements.append(Paragraph("CLÁUSULA SEGUNDA - DOS JUROS E ENCARGOS", clause_style))
    metodo_nome = {
        'simples': 'Juros Simples',
        'composto': 'Juros Compostos',
        'price': 'Tabela Price',
        'sac': 'Sistema de Amortização Constante (SAC)'
    }.get(emprestimo['metodo_calculo'], emprestimo['metodo_calculo'])
    
    texto_juros = f"""
    2.1. O valor emprestado será acrescido de juros remuneratórios à taxa de <b>{emprestimo['taxa_juros_mensal']}% ao mês</b>.<br/><br/>
    2.2. O método de cálculo utilizado será o <b>{metodo_nome}</b>.<br/><br/>
    2.3. O valor total a ser pago, incluindo principal e juros, será de <b>R$ {formatar_reais(emprestimo['valor_total_com_juros_centavos'])}</b>.
    """
    elements.append(Paragraph(texto_juros, normal_style))
    
    # Calcular valor da parcela se não existir (robustez)
    valor_parcela = emprestimo.get('valor_parcela')
    if not valor_parcela:
        valor_parcela = arredondar_centavos(emprestimo.get('valor_total_com_juros_centavos', 0) / max(emprestimo.get('prazo_meses', 1), 1))
    
    # Data primeiro vencimento com fallback
    data_venc = emprestimo.get('data_primeiro_vencimento', 'Conforme acordado')
    if hasattr(data_venc, 'strftime'):
        data_venc = data_venc.strftime('%d/%m/%Y')
    elif isinstance(data_venc, str) and 'T' in data_venc:
        data_venc = data_venc.split('T')[0]
    
    # Cláusula Terceira - Do Pagamento
    elements.append(Paragraph("CLÁUSULA TERCEIRA - DO PAGAMENTO", clause_style))
    texto_pagamento = f"""
    3.1. O DEVEDOR pagará ao CREDOR o valor total em <b>{emprestimo.get('prazo_meses', 1)} parcelas</b> mensais e consecutivas,
    no valor aproximado de <b>R$ {formatar_reais(valor_parcela)}</b> cada.<br/><br/>
    3.2. O vencimento da primeira parcela será em <b>{data_venc}</b>.<br/><br/>
    3.3. Os pagamentos deverão ser realizados até a data de vencimento de cada parcela.
    """
    elements.append(Paragraph(texto_pagamento, normal_style))
    
    # Cláusula Quarta - Da Mora
    elements.append(Paragraph("CLÁUSULA QUARTA - DA MORA E INADIMPLÊNCIA", clause_style))
    texto_mora = f"""
    4.1. Em caso de atraso no pagamento, incidirá multa de <b>{emprestimo.get('taxa_multa_atraso', 2)}%</b> sobre o valor da parcela.<br/><br/>
    4.2. Além da multa, serão cobrados juros de mora de <b>{emprestimo.get('taxa_juros_mora_diario', 0.033)}% ao dia</b>.<br/><br/>
    4.3. O não pagamento de qualquer parcela por prazo superior a 30 (trinta) dias importará no vencimento 
    antecipado de todas as parcelas vincendas, tornando-se exigível a totalidade do débito.
    """
    elements.append(Paragraph(texto_mora, normal_style))
    
    # Cláusula Quinta - Das Disposições Gerais
    elements.append(Paragraph("CLÁUSULA QUINTA - DAS DISPOSIÇÕES GERAIS", clause_style))
    texto_disposicoes = f"""
    5.1. O presente contrato obriga as partes e seus sucessores.<br/><br/>
    5.2. Qualquer tolerância do CREDOR não importará em novação ou renúncia de direitos.<br/><br/>
    5.3. As partes declaram que o presente instrumento é celebrado de boa-fé e livre de vícios.
    """
    elements.append(Paragraph(texto_disposicoes, normal_style))
    
    # Cláusula Sexta - Cláusulas Especiais/Personalizadas
    elements.append(Paragraph("CLÁUSULA SEXTA - CLÁUSULAS ESPECIAIS", clause_style))
    
    if clausulas_adicionais:
        texto_especiais = f"""
        As partes acordam as seguintes cláusulas especiais, que prevalecem sobre as demais em caso de conflito:<br/><br/>
        {clausulas_adicionais}
        """
    else:
        texto_especiais = """
        <b>ESPAÇO PARA CLÁUSULAS ESPECIAIS:</b><br/><br/>
        _________________________________________________________________________<br/><br/>
        _________________________________________________________________________<br/><br/>
        _________________________________________________________________________<br/><br/>
        _________________________________________________________________________<br/><br/>
        _________________________________________________________________________<br/><br/>
        _________________________________________________________________________<br/><br/>
        _________________________________________________________________________<br/><br/>
        <i>(Utilize este espaço para incluir condições especiais acordadas entre as partes)</i>
        """
    elements.append(Paragraph(texto_especiais, normal_style))
    
    # Cláusula Sétima - Do Foro
    elements.append(Paragraph("CLÁUSULA SÉTIMA - DO FORO", clause_style))
    texto_foro = f"""
    As partes elegem o foro da comarca de <b>{cliente['endereco']['cidade']}/{cliente['endereco']['estado']}</b> 
    para dirimir quaisquer dúvidas ou litígios oriundos do presente contrato, com renúncia expressa a qualquer outro,
    por mais privilegiado que seja.
    """
    elements.append(Paragraph(texto_foro, normal_style))
    
    # Assinaturas
    elements.append(Spacer(1, 30))
    texto_encerramento = f"""
    E, por estarem assim justos e contratados, as partes firmam o presente instrumento em 02 (duas) vias de igual 
    teor e forma, na presença de 02 (duas) testemunhas, para que produza seus efeitos legais.<br/><br/>
    <b>{cliente['endereco']['cidade']}/{cliente['endereco']['estado']}, {data_hoje}</b>
    """
    elements.append(Paragraph(texto_encerramento, normal_style))
    
    elements.append(Spacer(1, 40))
    
    assinaturas = """
    <br/><br/>
    _____________________________________________<br/>
    <b>CREDOR</b><br/><br/><br/><br/>
    
    _____________________________________________<br/>
    <b>DEVEDOR</b><br/><br/><br/><br/>
    
    <b>TESTEMUNHAS:</b><br/><br/>
    1. ___________________________________ CPF: ___________________<br/><br/>
    2. ___________________________________ CPF: ___________________
    """
    elements.append(Paragraph(assinaturas, normal_style))
    
    # Tabela de Parcelas (nova página)
    if parcelas:
        elements.append(PageBreak())
        elements.append(Paragraph("ANEXO I - TABELA DE PARCELAS", title_style))
        elements.append(Spacer(1, 20))
        
        table_data = [["Nº", "Vencimento", "Valor", "Status"]]
        for p in parcelas:
            # Status robusto - verifica 'pago', 'status' ou valor_pago_centavos
            status_val = p.get('status', '')
            is_pago = p.get('pago') or status_val == 'pago' or (p.get('valor_pago_centavos', 0) > 0)
            status = "Pago" if is_pago else "Pendente"
            
            # Data vencimento formatada
            data_venc = p.get('data_vencimento', '')
            if hasattr(data_venc, 'strftime'):
                data_venc = data_venc.strftime('%d/%m/%Y')
            elif isinstance(data_venc, str) and 'T' in data_venc:
                data_venc = data_venc.split('T')[0]
            
            table_data.append([
                str(p.get('numero_parcela', '?')),
                data_venc,
                f"R$ {formatar_reais(p.get('valor_total_centavos', p.get('valor', 0)))}",
                status
            ])
        
        table = Table(table_data, colWidths=[2*cm, 4*cm, 4*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ]))
        elements.append(table)


@router.post("/gerar")
async def gerar_contrato(
    request: ContratoRequest,
    current_user: Usuario = Depends(verificar_recurso("contratos_pdf"))  # Verifica acesso a contratos
):
    """Gera contrato em PDF com diferentes templates"""
    # Verificar se template personalizado requer plano avançado
    if request.template == "personalizado":
        pode, msg = await permissao_service.verificar_recurso(current_user, "contratos_personalizados")
        if not pode:
            raise HTTPException(status_code=403, detail=msg)
    
    context_id = get_user_context(current_user)
    
    # Determinar nome do credor (Dono da conta)
    credor_nome = current_user.nome
    if not is_owner(current_user):
        owner = await db.usuarios.find_one({"id": context_id})
        if owner:
            credor_nome = owner["nome"]
    
    emprestimo = await db.emprestimos.find_one({
        "id": request.emprestimo_id,
        "usuario_id": context_id
    }, {"_id": 0})
    
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    cliente = await db.clientes.find_one({
        "id": emprestimo["cliente_id"],
        "usuario_id": context_id
    }, {"_id": 0})
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Converter endereco se for string para objeto para compatibilidade com template
    if isinstance(cliente.get("endereco"), str):
        cliente["endereco"] = {
            "rua": cliente.get("endereco", ""),
            "numero": "S/N",
            "bairro": "Centro",
            "cidade": cliente.get("cidade", ""),
            "estado": cliente.get("estado", ""),
            "cep": cliente.get("cep", "")
        }
    
    parcelas = await db.parcelas.find(
        {"emprestimo_id": request.emprestimo_id, "usuario_id": context_id},
        {"_id": 0}
    ).sort("numero_parcela", 1).to_list(100)
    
    # Gerar PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
    elements = []
    styles = getSampleStyleSheet()
    
    # Selecionar template
    if request.template == "garantia":
        gerar_contrato_garantia(elements, styles, emprestimo, cliente, parcelas, credor_nome)
    elif request.template == "personalizado":
        gerar_contrato_personalizado(elements, styles, emprestimo, cliente, parcelas, credor_nome, request.clausulas_adicionais)
    else:  # padrao
        gerar_contrato_padrao(elements, styles, emprestimo, cliente, parcelas, credor_nome)
    
    doc.build(elements)
    buffer.seek(0)
    
    template_nome = {"padrao": "padrao", "garantia": "garantia", "personalizado": "personalizado"}.get(request.template, "padrao")
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=contrato_{template_nome}_{request.emprestimo_id[:8]}.pdf"}
    )


@router.get("/preview/{emprestimo_id}")
async def preview_contrato(
    emprestimo_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Retorna dados para preview do contrato"""
    emprestimo = await db.emprestimos.find_one({
        "id": emprestimo_id,
        "usuario_id": current_user.id
    }, {"_id": 0})
    
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    cliente = await db.clientes.find_one({
        "id": emprestimo["cliente_id"],
        "usuario_id": current_user.id
    }, {"_id": 0})
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Converter endereco se for string para objeto para compatibilidade com template
    if isinstance(cliente.get("endereco"), str):
        cliente["endereco"] = {
            "rua": cliente.get("endereco", ""),
            "numero": "S/N",
            "bairro": "Centro",
            "cidade": cliente.get("cidade", ""),
            "estado": cliente.get("estado", ""),
            "cep": cliente.get("cep", "")
        }
    
    parcelas = await db.parcelas.find(
        {"emprestimo_id": emprestimo_id, "usuario_id": current_user.id},
        {"_id": 0}
    ).sort("numero_parcela", 1).to_list(100)
    
    return {
        "emprestimo": emprestimo,
        "cliente": cliente,
        "parcelas": parcelas,
        "templates_disponiveis": ["padrao", "garantia", "personalizado"]
    }


@router.get("/templates")
async def listar_templates():
    """Lista os templates de contrato disponíveis"""
    return {
        "templates": [
            {
                "id": "padrao",
                "nome": "Contrato Padrão",
                "descricao": "Modelo básico com todas as cláusulas essenciais de empréstimo",
                "caracteristicas": [
                    "Dados das partes",
                    "Condições do empréstimo",
                    "Tabela de parcelas",
                    "Multa e juros de mora"
                ]
            },
            {
                "id": "garantia",
                "nome": "Contrato com Garantia",
                "descricao": "Inclui cláusulas específicas para garantias oferecidas",
                "caracteristicas": [
                    "Tudo do padrão",
                    "Cláusula de garantia",
                    "Execução da garantia",
                    "Campo para descrição da garantia"
                ]
            },
            {
                "id": "personalizado",
                "nome": "Contrato Personalizado",
                "descricao": "Crie seu próprio modelo de contrato com cláusulas especiais",
                "caracteristicas": [
                    "Tudo do padrão",
                    "Espaço para cláusulas especiais",
                    "Flexibilidade total"
                ]
            }
        ]
    }
