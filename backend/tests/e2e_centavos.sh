#!/usr/bin/env bash
# Fluxo E2E em reais na fronteira: cliente -> empréstimo Price 10k/12x/2% -> pagamentos -> estorno -> dashboard
set -e
API=https://cred-preview-app.preview.emergentagent.com
: "${KREDOR_QA_SENHA:?defina KREDOR_QA_SENHA}"
TOKEN=$(curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" -d '{"email":"qa.kredor@kredor.com.br","senha":"'"$KREDOR_QA_SENHA"'","turnstile_token":"x"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
H="Authorization: Bearer $TOKEN"; J="Content-Type: application/json"
CID=$(curl -s -X POST "$API/api/clientes" -H "$H" -H "$J" -d '{"nome":"Cliente Centavos","cpf_cnpj":"390.533.447-05","telefone":"11999990000","email":"c@c.com","endereco":{"rua":"Rua A","numero":"1","bairro":"Centro","cidade":"SP","estado":"SP","cep":"01000-000"}}' | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('id') or d)")
echo "cliente: $CID"
EMP=$(curl -s -X POST "$API/api/emprestimos" -H "$H" -H "$J" -d "{\"cliente_id\":\"$CID\",\"valor_principal\":10000,\"taxa_juros_mensal\":2,\"prazo_meses\":12,\"metodo_calculo\":\"tabela_price\"}")
echo "$EMP" | python3 -c "import sys,json;d=json.load(sys.stdin);print('emprestimo',{k:d.get(k) for k in ['valor_principal','valor_total_com_juros','valor_total_juros','status']})"
EID=$(echo "$EMP" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
PID=$(curl -s "$API/api/emprestimos/$EID/parcelas" -H "$H" | python3 -c "import sys,json;ps=json.load(sys.stdin);print(ps[0]['id']);import sys as s;s.stderr.write(str(len(ps))+' parcelas; soma principal='+str(round(sum(p['valor_principal'] for p in ps),2))+' p1='+str({k:ps[0][k] for k in ['valor_total','valor_pago','status']})+'\n')")
curl -s -X POST "$API/api/pagamentos" -H "$H" -H "$J" -d "{\"parcela_id\":\"$PID\",\"valor_pago\":500.10,\"metodo_pagamento\":\"pix\"}" | python3 -c "import sys,json;d=json.load(sys.stdin);print('pagamento parcial',{k:d.get(k) for k in ['valor_pago','valor_emprestimo']})"
PAG2=$(curl -s -X POST "$API/api/pagamentos" -H "$H" -H "$J" -d "{\"parcela_id\":\"$PID\",\"valor_pago\":445.50,\"metodo_pagamento\":\"pix\"}" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['id'])")
curl -s "$API/api/emprestimos/$EID/parcelas" -H "$H" | python3 -c "import sys,json;ps=json.load(sys.stdin);print('p1 apos 2 pagamentos',{k:ps[0][k] for k in ['valor_total','valor_pago','status']})"
mongosh --quiet gestorcred --eval 'const p=db.parcelas.findOne({id:"'$PID'"},{_id:0,valor_pago_centavos:1,valor_total_centavos:1,status:1}); print("mongo:", JSON.stringify(p))'
curl -s -X DELETE "$API/api/pagamentos/$PAG2" -H "$H"; echo
curl -s "$API/api/emprestimos/$EID/parcelas" -H "$H" | python3 -c "import sys,json;ps=json.load(sys.stdin);print('p1 apos estorno',{k:ps[0][k] for k in ['valor_total','valor_pago','status']})"
curl -s "$API/api/dashboard" -H "$H" | python3 -c "import sys,json;d=json.load(sys.stdin);print('dashboard',{k:d[k] for k in ['total_capital_emprestado','total_juros_a_receber','a_receber_mes','recebido_mes_atual']}, d['proximos_vencimentos'][:1])"
curl -s "$API/api/pagamentos" -H "$H" | python3 -c "import sys,json;ps=json.load(sys.stdin);print('lista pagamentos',[(p['valor_pago'],p.get('valor_emprestimo')) for p in ps][:3])"
echo "$EID" > /tmp/eid
