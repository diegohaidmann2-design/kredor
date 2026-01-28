"""
Rotas de Relatórios - Com Templates Profissionais
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime, timedelta, timezone
from io import BytesIO

from config import db
from models.relatorio import RelatorioRequest
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.permissao_service import verificar_plano_ativo, verificar_recurso
from utils.relatorio_templates import gerar_pdf_profissional
from utils.excel_templates import gerar_excel_profissional

router = APIRouter()


def get_periodo_datas(periodo: str, data_inicio: str = None, data_fim: str = None):
    """Calcula datas de início e fim baseado no período"""
    hoje = datetime.now(timezone.utc)
    
    if periodo == "hoje":
        inicio = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
        fim = hoje
    elif periodo == "semana":
        inicio = hoje - timedelta(days=7)
        fim = hoje
    elif periodo == "mes":
        inicio = hoje - timedelta(days=30)
        fim = hoje
    elif periodo == "trimestre":
        inicio = hoje - timedelta(days=90)
        fim = hoje
    elif periodo == "ano":
        inicio = hoje - timedelta(days=365)
        fim = hoje
    elif periodo == "personalizado":
        inicio = datetime.fromisoformat(data_inicio) if data_inicio else hoje - timedelta(days=30)
        fim = datetime.fromisoformat(data_fim) if data_fim else hoje
    else:
        inicio = hoje - timedelta(days=30)
        fim = hoje
    
    return inicio, fim


@router.post("/gerar")
async def gerar_relatorio(
    request: RelatorioRequest,
    current_user: Usuario = Depends(verificar_plano_ativo)  # Verifica plano ativo
):
    """Gera relatório profissional em PDF ou Excel com métricas e resumo executivo"""
    # Verificar se tem acesso a relatórios avançados para tipos específicos
    from services.permissao_service import permissao_service
    if request.tipo in ["inadimplencia", "fluxo_caixa"]:
        pode, msg = await permissao_service.verificar_recurso(current_user, "relatorios_avancados")
        if not pode:
            raise HTTPException(status_code=403, detail=msg)
    
    inicio, fim = get_periodo_datas(request.periodo, request.data_inicio, request.data_fim)
    periodo_str = f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
    
    user_filter = {"usuario_id": get_user_context(current_user)}
    
    # Variáveis para dados e métricas
    dados = []
    dados_resumo = []
    tipo_relatorio_nome = ""
    
    if request.tipo == "emprestimos":
        tipo_relatorio_nome = "Empréstimos"
        emprestimos = await db.emprestimos.find(user_filter, {"_id": 0}).to_list(1000)
        clientes = await db.clientes.find(user_filter, {"_id": 0, "id": 1, "nome": 1}).to_list(1000)
        clientes_map = {c["id"]: c["nome"] for c in clientes}
        
        # Calcular métricas
        total_emprestimos = len(emprestimos)
        valor_total = sum(e.get("valor_principal", 0) for e in emprestimos)
        emprestimos_ativos = len([e for e in emprestimos if e.get("status") == "ativo"])
        valor_medio = valor_total / total_emprestimos if total_emprestimos > 0 else 0
        
        # Dados resumo
        dados_resumo = [
            {"titulo": "Total de Empréstimos", "valor": total_emprestimos, "cor": "primaria"},
            {"titulo": "Empréstimos Ativos", "valor": emprestimos_ativos, "cor": "sucesso"},
            {"titulo": "Valor Total", "valor": f"R$ {valor_total:,.2f}", "cor": "secundaria"},
            {"titulo": "Valor Médio", "valor": f"R$ {valor_medio:,.2f}", "cor": "acento"},
        ]
        
        # Dados detalhados
        for e in emprestimos:
            dados.append({
                "Cliente": clientes_map.get(e["cliente_id"], "N/A"),
                "Valor Principal": f"R$ {e['valor_principal']:,.2f}",
                "Taxa Juros": f"{e['taxa_juros_mensal']}%",
                "Prazo": f"{e['prazo_meses']} meses",
                "Método": e["metodo_calculo"].upper(),
                "Status": e["status"].upper(),
                "Data": e.get("created_at", "")[:10] if isinstance(e.get("created_at"), str) else ""
            })
        
        titulo = f"Relatório de Empréstimos"
        
    elif request.tipo == "pagamentos":
        tipo_relatorio_nome = "Pagamentos"
        pagamentos = await db.pagamentos.find(user_filter, {"_id": 0}).to_list(1000)
        
        # Calcular métricas
        total_pagamentos = len(pagamentos)
        valor_total_pago = sum(p.get("valor_pago", 0) for p in pagamentos)
        
        # Agrupar por método
        metodos = {}
        for p in pagamentos:
            metodo = p.get("metodo_pagamento", "Não especificado")
            metodos[metodo] = metodos.get(metodo, 0) + 1
        
        metodo_mais_usado = max(metodos.items(), key=lambda x: x[1])[0] if metodos else "N/A"
        
        # Dados resumo
        dados_resumo = [
            {"titulo": "Total de Pagamentos", "valor": total_pagamentos, "cor": "primaria"},
            {"titulo": "Valor Total Recebido", "valor": f"R$ {valor_total_pago:,.2f}", "cor": "sucesso"},
            {"titulo": "Método Mais Usado", "valor": metodo_mais_usado, "cor": "secundaria"},
        ]
        
        # Dados detalhados
        for p in pagamentos:
            data_pag = p.get("data_pagamento", "")
            if isinstance(data_pag, str):
                data_formatada = data_pag[:10]
            else:
                data_formatada = data_pag.strftime("%d/%m/%Y") if data_pag else ""
            
            dados.append({
                "Data": data_formatada,
                "Valor Pago": f"R$ {p['valor_pago']:,.2f}",
                "Método": p.get("metodo_pagamento", "N/A"),
                "Parcela ID": p.get("parcela_id", "")[:8],
                "Observações": p.get("observacoes", "")[:30]
            })
        
        titulo = f"Relatório de Pagamentos"
        
    elif request.tipo == "clientes":
        tipo_relatorio_nome = "Clientes"
        clientes = await db.clientes.find(user_filter, {"_id": 0}).to_list(1000)
        
        # Calcular métricas
        total_clientes = len(clientes)
        clientes_ativos = len([c for c in clientes if c.get("status") == "ativo"])
        clientes_inativos = total_clientes - clientes_ativos
        
        # Dados resumo
        dados_resumo = [
            {"titulo": "Total de Clientes", "valor": total_clientes, "cor": "primaria"},
            {"titulo": "Clientes Ativos", "valor": clientes_ativos, "cor": "sucesso"},
            {"titulo": "Clientes Inativos", "valor": clientes_inativos, "cor": "texto_claro"},
        ]
        
        # Dados detalhados
        for c in clientes:
            dados.append({
                "Nome": c["nome"],
                "CPF/CNPJ": c["cpf_cnpj"],
                "Telefone": c.get("telefone", ""),
                "Email": c.get("email", ""),
                "Status": c.get("status", "").upper(),
                "Cidade": c.get("cidade", "")
            })
        
        titulo = f"Relatório de Clientes"
        
    elif request.tipo == "inadimplencia":
        tipo_relatorio_nome = "Inadimplência"
        hoje = datetime.now(timezone.utc).isoformat()
        parcelas_atrasadas = await db.parcelas.find({
            **user_filter,
            "status": {"$in": ["pendente", "parcial", "atrasado"]},
            "data_vencimento": {"$lt": hoje}
        }, {"_id": 0}).to_list(1000)
        
        emprestimos = await db.emprestimos.find(user_filter, {"_id": 0}).to_list(1000)
        emprestimos_map = {e["id"]: e for e in emprestimos}
        
        clientes = await db.clientes.find(user_filter, {"_id": 0}).to_list(1000)
        clientes_map = {c["id"]: c["nome"] for c in clientes}
        
        # Calcular métricas
        total_atrasadas = len(parcelas_atrasadas)
        valor_total_atrasado = sum(p.get("valor_total", 0) for p in parcelas_atrasadas)
        
        dias_atraso_medio = 0
        if total_atrasadas > 0:
            total_dias = sum(p.get("dias_atraso", 0) for p in parcelas_atrasadas)
            dias_atraso_medio = int(total_dias / total_atrasadas)
        
        # Dados resumo
        dados_resumo = [
            {"titulo": "Parcelas Atrasadas", "valor": total_atrasadas, "cor": "erro"},
            {"titulo": "Valor Total em Atraso", "valor": f"R$ {valor_total_atrasado:,.2f}", "cor": "alerta"},
            {"titulo": "Dias de Atraso Médio", "valor": f"{dias_atraso_medio} dias", "cor": "texto_claro"},
        ]
        
        # Dados detalhados
        for p in parcelas_atrasadas:
            emp = emprestimos_map.get(p["emprestimo_id"], {})
            cliente_nome = clientes_map.get(emp.get("cliente_id", ""), "N/A")
            dados.append({
                "Cliente": cliente_nome,
                "Nº Parcela": p["numero_parcela"],
                "Vencimento": p["data_vencimento"][:10],
                "Valor": f"R$ {p['valor_total']:,.2f}",
                "Dias em Atraso": p.get("dias_atraso", 0),
                "Status": p.get("status", "").upper()
            })
        
        titulo = f"Relatório de Inadimplência"
        
    elif request.tipo == "fluxo_caixa":
        tipo_relatorio_nome = "Fluxo de Caixa"
        pagamentos = await db.pagamentos.find(user_filter, {"_id": 0}).to_list(1000)
        emprestimos = await db.emprestimos.find(user_filter, {"_id": 0}).to_list(1000)
        
        total_entradas = sum(p.get("valor_pago", 0) for p in pagamentos)
        total_saidas = sum(e.get("valor_principal", 0) for e in emprestimos)
        saldo = total_entradas - total_saidas
        
        # Dados resumo
        dados_resumo = [
            {"titulo": "Total de Entradas", "valor": f"R$ {total_entradas:,.2f}", "cor": "sucesso"},
            {"titulo": "Total de Saídas", "valor": f"R$ {total_saidas:,.2f}", "cor": "erro"},
            {"titulo": "Saldo", "valor": f"R$ {saldo:,.2f}", "cor": "primaria" if saldo >= 0 else "alerta"},
        ]
        
        dados = [
            {"Tipo": "ENTRADAS (Pagamentos Recebidos)", "Quantidade": len(pagamentos), "Valor": f"R$ {total_entradas:,.2f}"},
            {"Tipo": "SAÍDAS (Empréstimos Concedidos)", "Quantidade": len(emprestimos), "Valor": f"R$ {total_saidas:,.2f}"},
            {"Tipo": "SALDO", "Quantidade": "-", "Valor": f"R$ {saldo:,.2f}"}
        ]
        
        titulo = f"Relatório de Fluxo de Caixa"
    else:
        raise HTTPException(status_code=400, detail="Tipo de relatório inválido")
    
    if not dados:
        raise HTTPException(status_code=404, detail="Nenhum dado encontrado para o período")
    
    # Gerar arquivo com templates profissionais
    if request.formato == "pdf":
        buffer = gerar_pdf_profissional(
            titulo=titulo,
            periodo=periodo_str,
            dados=dados,
            tipo_relatorio=tipo_relatorio_nome,
            dados_resumo=dados_resumo
        )
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=relatorio_{request.tipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"}
        )
    
    else:  # Excel
        buffer = gerar_excel_profissional(
            titulo=titulo,
            periodo=periodo_str,
            dados=dados,
            tipo_relatorio=tipo_relatorio_nome,
            dados_resumo=dados_resumo
        )
        
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=relatorio_{request.tipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"}
        )
