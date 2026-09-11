#!/usr/bin/env bash
# Fluxo E2E de empréstimo ABERTO (apenas_juros/sem_prazo): pagar -> gera próxima -> amortizar -> incorporar -> quitar
set -e
API=https://credito-app-12.preview.emergentagent.com
TOKEN=$(curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" -d '{"email":"qa.kredor@kredor.com.br","senha":"Kq!2026-fase1","turnstile_token":"x"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
H="Authorization: Bearer $TOKEN"; J="Content-Type: application/json"
CID=$(curl -s "$API/api/clientes" -H "$H" | python3 -c "import sys,json;d=json.load(sys.stdin);d=d if isinstance(d,list) else d.get('items') or d.get('clientes') or d.get('data');print(d[0]['id'])")
EMP=$(curl -s -X POST "$API/api/emprestimos" -H "$H" -H "$J" -d "{\"cliente_id\":\"$CID\",\"valor_principal\":1000,\"taxa_juros_mensal\":10,\"metodo_calculo\":\"apenas_juros\",\"sem_prazo\":true}")
echo "$EMP" | python3 -c "import sys,json;d=json.load(sys.stdin);print('aberto',{k:d.get(k) for k in ['valor_principal','valor_total_com_juros','status']} if 'id' in d else d)"
EID=$(echo "$EMP" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
PID=$(curl -s "$API/api/emprestimos/$EID/parcelas" -H "$H" | python3 -c "import sys,json;ps=json.load(sys.stdin);print(ps[0]['id']);sys.stderr.write('parcelas: '+str([(p['numero_parcela'],p['valor_total'],p['valor_juros']) for p in ps])+'\n')")
curl -s -X POST "$API/api/pagamentos" -H "$H" -H "$J" -d "{\"parcela_id\":\"$PID\",\"valor_pago\":100,\"metodo_pagamento\":\"pix\"}" | python3 -c "import sys,json;d=json.load(sys.stdin);print('pago juros',d.get('valor_pago'))"
curl -s "$API/api/emprestimos/$EID/parcelas" -H "$H" | python3 -c "import sys,json;ps=json.load(sys.stdin);print('apos pagamento:',[(p['numero_parcela'],p['valor_total'],p['status']) for p in ps])"
curl -s -X POST "$API/api/emprestimos/$EID/amortizar" -H "$H" -H "$J" -d '{"valor_amortizacao":300.33,"metodo_pagamento":"pix","recalcular_juros":true}' | python3 -c "import sys,json;d=json.load(sys.stdin);print('amortizar',{k:d.get(k) for k in ['principal_anterior','principal_atual','novo_principal','valor_amortizado','message','detail']})"
curl -s -X POST "$API/api/emprestimos/$EID/incorporar-juros" -H "$H" -H "$J" -d '{"valor_juros":50.5,"baixar_parcelas":true,"recalcular_juros":true}' | python3 -c "import sys,json;d=json.load(sys.stdin);print('incorporar',{k:d.get(k) for k in ['valor_incorporado','principal_anterior','principal_atual','detail']})"
curl -s "$API/api/emprestimos/$EID" -H "$H" | python3 -c "import sys,json;d=json.load(sys.stdin);print('emprestimo agora: principal',d.get('valor_principal'))"
mongosh --quiet gestorcred --eval 'const e=db.emprestimos.findOne({id:"'$EID'"},{_id:0,valor_principal_centavos:1}); print("mongo principal_centavos:", e.valor_principal_centavos, typeof e.valor_principal_centavos)'
curl -s "$API/api/emprestimos/abertos/resumo" -H "$H" | python3 -c "import sys,json;d=json.load(sys.stdin);print('resumo abertos totais',d['totais'], 'item0', {k:d['itens'][0].get(k) for k in ['valor_principal','juros_gerado','juros_em_aberto']} if d['itens'] else None)"
curl -s -X POST "$API/api/emprestimos/$EID/quitar-aberto" -H "$H" -H "$J" -d '{}' | python3 -c "import sys,json;d=json.load(sys.stdin);print('quitar',{k:d.get(k) for k in ['valor_total','valor_pago','valor_total_emprestimo','message','detail']})"
curl -s "$API/api/emprestimos/$EID/ajustes-capital" -H "$H" | python3 -c "import sys,json;d=json.load(sys.stdin);print('ajustes',[(a['tipo'],a['valor'],a.get('principal_anterior'),a.get('principal_apos')) for a in (d if isinstance(d,list) else d.get('ajustes',[]))])"
