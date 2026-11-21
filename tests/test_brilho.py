import numpy as np
import pytest

from brilho import DetectorLuz, calcular_brilho, recortar_roi


def imagem(valor: int, altura=100, largura=200):
    return np.full((altura, largura, 3), valor, np.uint8)


def test_brilho_de_imagem_uniforme():
    assert calcular_brilho(imagem(0)) == pytest.approx(0)
    assert calcular_brilho(imagem(200)) == pytest.approx(200)


def test_imagem_clara_tem_mais_brilho_que_escura():
    assert calcular_brilho(imagem(180)) > calcular_brilho(imagem(40))


def test_roi_mede_so_a_regiao():
    img = imagem(20)
    img[0:20, :] = 250  # "teto" iluminado
    assert calcular_brilho(img, roi=(0, 0, 200, 20)) == pytest.approx(250)
    assert calcular_brilho(img) < 100


def test_roi_fora_da_imagem_da_erro():
    with pytest.raises(ValueError):
        recortar_roi(imagem(10), (500, 500, 10, 10))


def test_detector_luz_com_histerese():
    luz = DetectorLuz(limiar=100, margem=5)
    assert luz.atualizar(150) is True
    assert luz.atualizar(98) is True    # dentro da margem: mantém ACESA
    assert luz.atualizar(94) is False   # abaixo de limiar - margem: APAGADA
    assert luz.atualizar(103) is False  # dentro da margem: mantém APAGADA
    assert luz.atualizar(106) is True
