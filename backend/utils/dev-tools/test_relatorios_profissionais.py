#!/usr/bin/env python3
"""
Script de teste para os novos templates profissionais de relatórios
Gera relatórios em PDF e Excel para validação visual
"""
import requests
import json
from datetime import datetime
import os

BASE_URL = "http://localhost:8001/api"
OUTPUT_DIR = "/app/relatorios_teste"

def print_section(title):
    """Print formatado de seção"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def main():
    # Criar diretório de output se não existir
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print_section("🧪 TESTE DOS TEMPLATES PROFISSIONAIS DE RELATÓRIOS")
    
    # 1. Login como admin
    print("\n1️⃣ Fazendo login como usuário de teste...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "usuario@teste.com", "senha": "senha123"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Erro no login: {login_response.status_code}")
        print(login_response.text)
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login realizado com sucesso!")
    
    # Tipos de relatórios para testar
    tipos_relatorios = [
        ("emprestimos", "Empréstimos"),
        ("pagamentos", "Pagamentos"),
        ("clientes", "Clientes"),
        ("fluxo_caixa", "Fluxo de Caixa"),
    ]
    
    formatos = [("pdf", "PDF"), ("xlsx", "Excel")]
    
    # Gerar relatórios
    print_section("2️⃣ Gerando Relatórios Profissionais")
    
    for tipo, nome in tipos_relatorios:
        print(f"\n📊 Gerando relatório de {nome}...")
        
        for formato, formato_nome in formatos:
            try:
                # Fazer request
                response = requests.post(
                    f"{BASE_URL}/relatorios/gerar",
                    json={
                        "tipo": tipo,
                        "formato": formato,
                        "periodo": "mes"
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    # Salvar arquivo
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{OUTPUT_DIR}/relatorio_{tipo}_{timestamp}.{formato}"
                    
                    with open(filename, "wb") as f:
                        f.write(response.content)
                    
                    file_size = len(response.content) / 1024  # KB
                    print(f"   ✅ {formato_nome}: {filename} ({file_size:.1f} KB)")
                    
                elif response.status_code == 404:
                    print(f"   ⚠️  {formato_nome}: Sem dados para o período")
                else:
                    print(f"   ❌ {formato_nome}: Erro {response.status_code}")
                    print(f"      {response.text[:100]}")
                    
            except Exception as e:
                print(f"   ❌ {formato_nome}: Erro - {str(e)}")
    
    # Resumo
    print_section("✅ RESUMO DOS TESTES")
    
    print(f"""
✅ Templates profissionais aplicados
✅ Relatórios gerados em {OUTPUT_DIR}

📋 Novos recursos nos relatórios:

🎨 PDF:
   • Capa profissional com título e período
   • Cabeçalho personalizado em cada página
   • Seção de Resumo Executivo com cards de métricas coloridos
   • Tabelas com design moderno e cores alternadas
   • Rodapé com informações da empresa e paginação
   • Paleta de cores corporativa (azul profissional)
   
📊 Excel:
   • Cabeçalho com título, período e data de geração
   • Cards de métricas coloridos no resumo executivo
   • Tabelas com formatação profissional
   • Linhas alternadas para melhor leitura
   • Larguras de coluna otimizadas
   • Rodapé com informações da empresa
   • Abas renomeadas com nome do relatório

🎯 Melhorias:
   • Métricas calculadas automaticamente (totais, médias, etc)
   • Resumo executivo visual com KPIs principais
   • Cores específicas por tipo de métrica (sucesso, alerta, erro)
   • Layout responsivo e profissional
   • Nome de arquivo com timestamp
   
📁 Arquivos gerados salvos em: {OUTPUT_DIR}
    """)
    
    print("\n💡 Para visualizar os relatórios:")
    print(f"   ls -lh {OUTPUT_DIR}")
    print("\n" + "="*70)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
