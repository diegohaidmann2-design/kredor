"""
Testes das correções da Fase 2 (2.4 exc_info, 2.6 migração/limpeza de centavos).
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.logging_service import get_logger, setup_logging
from scripts.migrar_para_centavos import _converter, _montar_update
from scripts.corrigir_centavos_float import _para_int_centavos


# ==================== 2.4 exc_info=True no _log ====================

class _Captura(logging.Handler):
    def __init__(self):
        super().__init__()
        self.registros = []

    def emit(self, record):
        self.registros.append(record)


def test_error_exc_info_true_gera_traceback_no_registro():
    setup_logging()
    log = get_logger("teste.exc")
    handler = _Captura()
    logging.getLogger().addHandler(handler)
    try:
        try:
            1 / 0
        except ZeroDivisionError:
            log.error("Traceback do erro", exc_info=True)
    finally:
        logging.getLogger().removeHandler(handler)

    assert handler.registros, "nenhum registro capturado"
    rec = handler.registros[-1]
    # exc_info deve ser a tupla (tipo, valor, tb) — nunca o booleano True.
    assert isinstance(rec.exc_info, tuple)
    assert rec.exc_info[0] is ZeroDivisionError


# ==================== 2.6 migração escreve só inteiros ====================

def test_converter_aceita_numeros_e_string_numerica():
    assert _converter(1234.56) == 123456
    assert _converter(1234) == 123400
    assert _converter("1234.56") == 123456


def test_converter_rejeita_valores_invalidos():
    for invalido in ["", None, True, False, {"$numberDecimal": "10"}, "abc"]:
        assert _converter(invalido) is None, f"deveria rejeitar {invalido!r}"


def test_montar_update_nao_grava_valor_nao_convertivel():
    doc = {"_id": "x", "valor_principal": "", "valor_total_com_juros": 100.0}
    op = _montar_update(doc, ["valor_principal", "valor_total_com_juros"], "emprestimos")
    setados = op._doc["$set"]
    # o campo convertível entra; o inválido ('') NÃO cria campo _centavos
    assert setados.get("valor_total_com_juros_centavos") == 10000
    assert "valor_principal_centavos" not in setados


def test_para_int_centavos_normaliza_tipos():
    assert _para_int_centavos(12345.0) == 12345
    assert _para_int_centavos("12345") == 12345
    assert _para_int_centavos(12345) == 12345
    assert _para_int_centavos(None) is None
    assert _para_int_centavos(True) is None
