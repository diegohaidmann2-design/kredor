"""Tarefa 3.4.1 - teto de prazo no endpoint público de simulação (proteção DoS).

Critério 3: no teto máximo de cada periodicidade a simulação deve completar em
menos de 1 segundo e com pico de memória abaixo de 50 MB.
"""
import time
import tracemalloc

import pytest
from pydantic import ValidationError

from models.emprestimo import SimulacaoRequest
from routes.emprestimos import executar_simulacao

TETO = {
    "mensal": {"prazo_meses": 600, "taxa_juros_mensal": 2.0},
    "semanal": {"prazo_semanas": 2_600, "taxa_juros_semanal": 0.5},
    "diario": {"prazo_dias": 18_250, "taxa_juros_diaria": 0.1},
}


@pytest.mark.parametrize("periodicidade,extra", list(TETO.items()))
def test_simulacao_no_teto_e_barata(periodicidade, extra):
    req = SimulacaoRequest(
        valor_principal=100000,
        metodo_calculo="juros_simples",
        periodicidade=periodicidade,
        **extra,
    )

    tracemalloc.start()
    inicio = time.perf_counter()
    resposta = executar_simulacao(req)
    duracao = time.perf_counter() - inicio
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    pico_mb = pico / (1024 * 1024)
    n_parcelas = len(resposta.parcelas)
    print(f"{periodicidade}: {n_parcelas} parcelas, {duracao*1000:.1f} ms, pico {pico_mb:.1f} MB")

    assert duracao < 1.0, f"{periodicidade}: {duracao:.2f}s excede 1s"
    assert pico_mb < 50.0, f"{periodicidade}: pico {pico_mb:.1f} MB excede 50 MB"


@pytest.mark.parametrize("campo,valor", [
    ("prazo_meses", 601),
    ("prazo_semanas", 2_601),
    ("prazo_dias", 18_251),
])
def test_prazo_acima_do_teto_rejeitado(campo, valor):
    with pytest.raises(ValidationError):
        SimulacaoRequest(
            valor_principal=100000,
            metodo_calculo="juros_simples",
            **{campo: valor},
        )
