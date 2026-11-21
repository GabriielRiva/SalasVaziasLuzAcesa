import pytest

from estado import Estado, MonitorSala


def test_sala_ocupada_nunca_alerta():
    m = MonitorSala(tolerancia_s=5)
    for t in range(0, 60):
        assert m.atualizar(True, True, t) == []
    assert m.estado == Estado.OCUPADA
    assert m.qtd_alertas == 0


def test_sala_vazia_e_apagada_esta_ok():
    m = MonitorSala(tolerancia_s=5)
    m.atualizar(False, False, 0)
    assert m.estado == Estado.APAGADA


def test_alerta_so_depois_da_tolerancia():
    m = MonitorSala(tolerancia_s=10)
    m.atualizar(False, True, 0)
    assert m.estado == Estado.VERIFICANDO
    m.atualizar(False, True, 9.9)
    assert m.estado == Estado.VERIFICANDO
    eventos = m.atualizar(False, True, 10)
    assert m.estado == Estado.ALERTA
    assert [e.tipo for e in eventos] == ["ALERTA_INICIO"]
    # não repete o alerta enquanto continua na mesma situação
    assert m.atualizar(False, True, 15) == []


def test_pessoa_sumindo_por_instantes_nao_gera_alerta():
    """Detector perde a pessoa por 2 s: não pode alarmar."""
    m = MonitorSala(tolerancia_s=10)
    m.atualizar(True, True, 0)
    m.atualizar(False, True, 1)
    m.atualizar(False, True, 3)
    m.atualizar(True, True, 3.1)
    assert m.qtd_alertas == 0
    assert m.estado == Estado.OCUPADA


def test_alerta_termina_quando_apagam_a_luz():
    m = MonitorSala(tolerancia_s=10)
    m.atualizar(False, True, 0)
    m.atualizar(False, True, 12)
    eventos = m.atualizar(False, False, 30)
    assert eventos[0].tipo == "ALERTA_FIM"
    assert eventos[0].motivo == "Luz foi apagada"
    assert eventos[0].desperdicio_s == pytest.approx(30)
    assert m.tempo_total_desperdicio_s == pytest.approx(30)
    assert m.estado == Estado.APAGADA


def test_alerta_termina_quando_alguem_entra():
    m = MonitorSala(tolerancia_s=5)
    m.atualizar(False, True, 0)
    m.atualizar(False, True, 6)
    eventos = m.atualizar(True, True, 8)
    assert eventos[0].motivo == "Pessoa entrou na sala"
    assert m.estado == Estado.OCUPADA


def test_finalizar_fecha_alerta_aberto():
    m = MonitorSala(tolerancia_s=5)
    m.atualizar(False, True, 0)
    m.atualizar(False, True, 6)
    eventos = m.finalizar(20)
    assert eventos[0].tipo == "ALERTA_FIM"
    assert m.tempo_total_desperdicio_s == pytest.approx(20)


def test_varios_alertas_somam_desperdicio():
    m = MonitorSala(tolerancia_s=5)
    m.atualizar(False, True, 0)
    m.atualizar(False, True, 5)
    m.atualizar(True, True, 10)     # 10 s de desperdício
    m.atualizar(False, True, 20)
    m.atualizar(False, True, 26)
    m.atualizar(False, False, 40)   # 20 s de desperdício
    assert m.qtd_alertas == 2
    assert m.tempo_total_desperdicio_s == pytest.approx(30)
