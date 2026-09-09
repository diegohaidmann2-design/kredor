#!/usr/bin/env python3
"""
Script de Geração de Dados Demo para Kredor
Cria dados realistas para demonstração e testes do sistema
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from random import choice, randint, uniform
from config import db
import bcrypt


# Dados realistas para geração
NOMES = [
    "João Silva", "Maria Santos", "Pedro Oliveira", "Ana Costa", "Carlos Souza",
    "Fernanda Lima", "Ricardo Alves", "Juliana Rocha", "Paulo Pereira", "Camila Dias",
    "Bruno Martins", "Beatriz Ferreira", "Lucas Ribeiro", "Larissa Gomes", "Rafael Cardoso",
    "Tatiana Mendes", "Gustavo Barros", "Mariana Araújo", "Rodrigo Castro", "Patricia Moura",
    "Eduardo Ramos", "Vanessa Correia", "Thiago Monteiro", "Isabela Freitas", "Diego Pinto"
]

EMPRESAS = [
    "Tech Solutions Ltda", "Comercial ABC", "Indústria XYZ S.A.", "Serviços JK",
    "Loja do Centro", "Padaria São José", "Restaurante Bom Sabor", "Auto Peças Norte",
    "Farmácia Popular", "Mercado do Bairro"
]

CIDADES = [
    ("São Paulo", "SP"), ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"),
    ("Porto Alegre", "RS"), ("Curitiba", "PR"), ("Salvador", "BA"),
    ("Brasília", "DF"), ("Fortaleza", "CE"), ("Recife", "PE"), ("Manaus", "AM")
]

METODOS_CALCULO = ["price", "sac", "juros_simples", "juros_compostos"]
STATUS_EMPRESTIMO = ["ativo", "quitado", "inadimplente"]
METODOS_PAGAMENTO = ["pix", "boleto", "transferencia", "cartao", "dinheiro"]


def gerar_cpf():
    """Gera um CPF fictício mas válido no formato"""
    return f"{randint(100, 999)}.{randint(100, 999)}.{randint(100, 999)}-{randint(10, 99)}"


def gerar_cnpj():
    """Gera um CNPJ fictício mas válido no formato"""
    return f"{randint(10, 99)}.{randint(100, 999)}.{randint(100, 999)}/0001-{randint(10, 99)}"


def gerar_telefone():
    """Gera um telefone fictício"""
    return f"({randint(11, 99)}) {randint(90000, 99999)}-{randint(1000, 9999)}"


def gerar_email(nome):
    """Gera um email fictício baseado no nome"""
    nome_email = nome.lower().replace(" ", ".").replace("ç", "c").replace("ã", "a")
    dominios = ["email.com", "exemplo.com", "teste.com", "demo.com.br"]
    return f"{nome_email}@{choice(dominios)}"


def calcular_parcelas_price(valor, taxa_mensal, prazo):
    """Calcula o valor da parcela pelo método Price"""
    taxa = taxa_mensal / 100
    parcela = valor * (taxa * (1 + taxa) ** prazo) / ((1 + taxa) ** prazo - 1)
    return round(parcela, 2)


async def criar_usuarios_demo(usuario_admin_id):
    """Cria usuários de demonstração"""
    print("\n📝 Criando usuários de demonstração...")
    
    usuarios_criados = []
    
    # Usuário teste que já existe - apenas retornar ID
    usuario_teste = await db.usuarios.find_one({"email": "usuario@teste.com"})
    if usuario_teste:
        usuarios_criados.append(usuario_teste["id"])
        print(f"   ✅ Usuário teste já existe: usuario@teste.com")
    
    # Criar mais 2 usuários demo
    for i in range(1, 3):
        usuario_id = str(uuid.uuid4())
        # Hash a senha corretamente com bcrypt
        senha_hash = bcrypt.hashpw("demo123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        await db.usuarios.insert_one({
            "id": usuario_id,
            "nome": f"Usuário Demo {i}",
            "email": f"demo{i}@kredor.com.br",
            "senha": senha_hash,
            "perfil": "usuario",
            "plano": "premium" if i == 1 else "basico",
            "plano_ativo": True,
            "data_expiracao_plano": (datetime.utcnow() + timedelta(days=365)).isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "deleted": False
        })
        
        usuarios_criados.append(usuario_id)
        print(f"   ✅ Usuário criado: demo{i}@kredor.com.br (senha: demo123)")
    
    # Admin também terá dados
    usuarios_criados.insert(0, usuario_admin_id)
    
    return usuarios_criados


async def criar_clientes_demo(usuarios_ids):
    """Cria clientes de demonstração"""
    print("\n👥 Criando clientes de demonstração...")
    
    clientes_criados = []
    total_clientes = 30
    
    for i in range(total_clientes):
        usuario_id = choice(usuarios_ids)
        cliente_id = str(uuid.uuid4())
        
        # Decidir se é pessoa física ou jurídica
        is_pj = i % 4 == 0  # 25% empresas
        
        if is_pj:
            nome = choice(EMPRESAS)
            cpf_cnpj = gerar_cnpj()
        else:
            nome = choice(NOMES)
            cpf_cnpj = gerar_cpf()
        
        cidade, estado = choice(CIDADES)
        
        await db.clientes.insert_one({
            "id": cliente_id,
            "usuario_id": usuario_id,
            "nome": nome,
            "cpf_cnpj": cpf_cnpj,
            "telefone": gerar_telefone(),
            "email": gerar_email(nome),
            "endereco": f"Rua {choice(['das Flores', 'Principal', 'Central', 'do Comércio'])}, {randint(1, 999)}",
            "cidade": cidade,
            "estado": estado,
            "cep": f"{randint(10000, 99999)}-{randint(100, 999)}",
            "status": "ativo" if i < 25 else "inativo",
            "observacoes": f"Cliente {'corporativo' if is_pj else 'pessoa física'} - Demo",
            "created_at": (datetime.utcnow() - timedelta(days=randint(1, 180))).isoformat(),
            "deleted": False
        })
        
        clientes_criados.append({"id": cliente_id, "usuario_id": usuario_id, "nome": nome})
        
        if (i + 1) % 10 == 0:
            print(f"   ✅ {i + 1}/{total_clientes} clientes criados...")
    
    print(f"   ✅ Total: {total_clientes} clientes criados")
    return clientes_criados


async def criar_emprestimos_demo(clientes):
    """Cria empréstimos de demonstração"""
    print("\n💰 Criando empréstimos de demonstração...")
    
    emprestimos_criados = []
    total_emprestimos = 40
    
    for i in range(total_emprestimos):
        cliente = choice(clientes)
        emprestimo_id = str(uuid.uuid4())
        
        # Valores variados
        valor_principal_centavos = round(uniform(1000, 50000), 2)
        taxa_juros = round(uniform(1.5, 5.0), 2)
        prazo_meses = choice([6, 12, 18, 24, 36, 48])
        metodo = choice(METODOS_CALCULO)
        
        # Calcular valor total com juros (simplificado)
        if metodo == "price":
            parcela_valor = calcular_parcelas_price(valor_principal_centavos, taxa_juros, prazo_meses)
            valor_total_centavos = parcela_valor * prazo_meses
        elif metodo == "juros_simples":
            juros_total = valor_principal_centavos * (taxa_juros / 100) * prazo_meses
            valor_total_centavos = valor_principal_centavos + juros_total
        else:
            valor_total_centavos = valor_principal_centavos * (1.2 + (prazo_meses * 0.01))  # Aproximado
        
        valor_total_centavos = round(valor_total_centavos, 2)
        
        # Status baseado em probabilidade
        status = choice(["ativo"] * 7 + ["quitado"] * 2 + ["inadimplente"] * 1)
        
        data_inicio = datetime.utcnow() - timedelta(days=randint(30, 365))
        
        await db.emprestimos.insert_one({
            "id": emprestimo_id,
            "usuario_id": cliente["usuario_id"],
            "cliente_id": cliente["id"],
            "valor_principal_centavos": valor_principal_centavos,
            "taxa_juros_mensal": taxa_juros,
            "prazo_meses": prazo_meses,
            "metodo_calculo": metodo,
            "valor_total_com_juros_centavos": valor_total_centavos,
            "status": status,
            "data_inicio": data_inicio.isoformat(),
            "observacoes": f"Empréstimo demo - {metodo.upper()}",
            "created_at": data_inicio.isoformat(),
            "deleted": False
        })
        
        emprestimos_criados.append({
            "id": emprestimo_id,
            "usuario_id": cliente["usuario_id"],
            "cliente_id": cliente["id"],
            "cliente_nome": cliente["nome"],
            "valor_total_centavos": valor_total_centavos,
            "prazo_meses": prazo_meses,
            "status": status,
            "data_inicio": data_inicio
        })
        
        if (i + 1) % 10 == 0:
            print(f"   ✅ {i + 1}/{total_emprestimos} empréstimos criados...")
    
    print(f"   ✅ Total: {total_emprestimos} empréstimos criados")
    return emprestimos_criados


async def criar_parcelas_demo(emprestimos):
    """Cria parcelas para os empréstimos"""
    print("\n📅 Criando parcelas de demonstração...")
    
    total_parcelas = 0
    
    for emprestimo in emprestimos:
        prazo = emprestimo["prazo_meses"]
        valor_parcela = round(emprestimo["valor_total_centavos"] / prazo, 2)
        
        for num_parcela in range(1, prazo + 1):
            parcela_id = str(uuid.uuid4())
            
            # Calcular data de vencimento
            data_vencimento = emprestimo["data_inicio"] + timedelta(days=30 * num_parcela)
            
            # Determinar status da parcela
            hoje = datetime.utcnow()
            
            if emprestimo["status"] == "quitado":
                status = "pago"
                valor_pago_centavos = valor_parcela
                data_pagamento = data_vencimento - timedelta(days=randint(0, 5))
            elif data_vencimento < hoje:
                # Parcela vencida
                probabilidade = randint(1, 100)
                if probabilidade <= 70:  # 70% pagas
                    status = "pago"
                    valor_pago_centavos = valor_parcela
                    data_pagamento = data_vencimento + timedelta(days=randint(0, 10))
                elif probabilidade <= 85:  # 15% pagas parcialmente
                    status = "parcial"
                    valor_pago_centavos = round(valor_parcela * uniform(0.3, 0.8), 2)
                    data_pagamento = None
                else:  # 15% atrasadas
                    status = "atrasado"
                    valor_pago_centavos = 0
                    data_pagamento = None
            else:
                # Parcela futura
                status = "pendente"
                valor_pago_centavos = 0
                data_pagamento = None
            
            # Calcular dias de atraso
            dias_atraso = 0
            if status in ["atrasado", "parcial"] and data_vencimento < hoje:
                dias_atraso = (hoje - data_vencimento).days
            
            await db.parcelas.insert_one({
                "id": parcela_id,
                "emprestimo_id": emprestimo["id"],
                "usuario_id": emprestimo["usuario_id"],
                "numero_parcela": num_parcela,
                "valor_principal_centavos": round(valor_parcela * 0.85, 2),
                "valor_juros_centavos": round(valor_parcela * 0.15, 2),
                "valor_total_centavos": valor_parcela,
                "valor_pago_centavos": valor_pago_centavos,
                "status": status,
                "data_vencimento": data_vencimento.isoformat(),
                "data_pagamento": data_pagamento.isoformat() if data_pagamento else None,
                "dias_atraso": dias_atraso,
                "created_at": emprestimo["data_inicio"].isoformat(),
                "deleted": False
            })
            
            total_parcelas += 1
    
    print(f"   ✅ Total: {total_parcelas} parcelas criadas")
    return total_parcelas


async def criar_pagamentos_demo(emprestimos):
    """Cria registros de pagamentos"""
    print("\n💳 Criando pagamentos de demonstração...")
    
    total_pagamentos = 0
    
    for emprestimo in emprestimos:
        # Buscar parcelas pagas deste empréstimo
        parcelas_pagas = await db.parcelas.find({
            "emprestimo_id": emprestimo["id"],
            "status": {"$in": ["pago", "parcial"]}
        }).to_list(1000)
        
        for parcela in parcelas_pagas:
            pagamento_id = str(uuid.uuid4())
            
            await db.pagamentos.insert_one({
                "id": pagamento_id,
                "usuario_id": emprestimo["usuario_id"],
                "emprestimo_id": emprestimo["id"],
                "parcela_id": parcela["id"],
                "valor_pago_centavos": parcela["valor_pago_centavos"],
                "metodo_pagamento": choice(METODOS_PAGAMENTO),
                "data_pagamento": parcela["data_pagamento"],
                "observacoes": f"Pagamento parcela {parcela['numero_parcela']} - {emprestimo['cliente_nome']}",
                "created_at": parcela["data_pagamento"],
                "deleted": False
            })
            
            total_pagamentos += 1
    
    print(f"   ✅ Total: {total_pagamentos} pagamentos criados")
    return total_pagamentos


async def criar_notificacoes_demo(usuarios_ids):
    """Cria notificações de demonstração"""
    print("\n🔔 Criando notificações de demonstração...")
    
    tipos_notificacao = [
        ("pagamento_recebido", "Pagamento recebido", "O pagamento da parcela foi confirmado."),
        ("parcela_vencendo", "Parcela vencendo", "Uma parcela vencerá em 3 dias."),
        ("parcela_atrasada", "Parcela atrasada", "Existe uma parcela em atraso."),
        ("emprestimo_quitado", "Empréstimo quitado", "Parabéns! O empréstimo foi quitado."),
    ]
    
    total_notificacoes = 0
    
    for usuario_id in usuarios_ids:
        # Criar 5-10 notificações por usuário
        num_notif = randint(5, 10)
        
        for i in range(num_notif):
            tipo, titulo, mensagem = choice(tipos_notificacao)
            
            await db.notificacoes.insert_one({
                "id": str(uuid.uuid4()),
                "usuario_id": usuario_id,
                "tipo": tipo,
                "titulo": titulo,
                "mensagem": mensagem,
                "lida": i < num_notif - 3,  # Últimas 3 não lidas
                "created_at": (datetime.utcnow() - timedelta(days=randint(0, 30))).isoformat(),
                "deleted": False
            })
            
            total_notificacoes += 1
    
    print(f"   ✅ Total: {total_notificacoes} notificações criadas")
    return total_notificacoes


async def main():
    """Função principal"""
    print("=" * 70)
    print("🚀 GERADOR DE DADOS DEMO - Kredor")
    print("=" * 70)
    print("\nEste script irá popular o banco de dados com dados de demonstração.")
    print("Ideal para testes, apresentações e desenvolvimento.\n")
    
    # Confirmar execução
    confirmacao = input("Deseja continuar? (s/n): ").lower().strip()
    if confirmacao != 's':
        print("\n❌ Operação cancelada.")
        return
    
    inicio = datetime.now()
    
    # Buscar usuário admin
    admin = await db.usuarios.find_one({"email": "admin@sgej.com"})
    if not admin:
        print("\n❌ Usuário admin não encontrado! Execute o seeder primeiro.")
        return
    
    print(f"\n✅ Usuário admin encontrado: {admin['email']}")
    
    # Criar dados
    usuarios = await criar_usuarios_demo(admin["id"])
    clientes = await criar_clientes_demo(usuarios)
    emprestimos = await criar_emprestimos_demo(clientes)
    await criar_parcelas_demo(emprestimos)
    await criar_pagamentos_demo(emprestimos)
    await criar_notificacoes_demo(usuarios)
    
    # Resumo final
    fim = datetime.now()
    duracao = (fim - inicio).total_seconds()
    
    print("\n" + "=" * 70)
    print("✅ DADOS DEMO CRIADOS COM SUCESSO!")
    print("=" * 70)
    
    # Estatísticas
    total_usuarios = len(usuarios)
    total_clientes = len(clientes)
    total_emprestimos = len(emprestimos)
    total_parcelas = await db.parcelas.count_documents({})
    total_pagamentos = await db.pagamentos.count_documents({})
    total_notificacoes = await db.notificacoes.count_documents({})
    
    print(f"\n📊 ESTATÍSTICAS:")
    print(f"   • Usuários:      {total_usuarios:>6}")
    print(f"   • Clientes:      {total_clientes:>6}")
    print(f"   • Empréstimos:   {total_emprestimos:>6}")
    print(f"   • Parcelas:      {total_parcelas:>6}")
    print(f"   • Pagamentos:    {total_pagamentos:>6}")
    print(f"   • Notificações:  {total_notificacoes:>6}")
    
    print(f"\n⏱️  Tempo de execução: {duracao:.2f} segundos")
    
    print("\n📝 CREDENCIAIS DE ACESSO:")
    print("   • Admin:   admin@sgej.com    / admin123")
    print("   • Demo 1:  demo1@kredor.com.br / demo123 (Premium)")
    print("   • Demo 2:  demo2@kredor.com.br / demo123 (Básico)")
    print("   • Teste:   usuario@teste.com   / senha123")
    
    print("\n💡 DICA: Use esses dados para:")
    print("   • Testar funcionalidades do sistema")
    print("   • Demonstrações para clientes")
    print("   • Desenvolvimento de novas features")
    print("   • Testes de relatórios e dashboards")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n\n❌ Erro durante a execução: {e}")
        import traceback
        traceback.print_exc()
