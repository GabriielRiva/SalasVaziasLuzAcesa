"""
Análise de brilho do ambiente.

A ideia é simples: uma sala com a luz acesa gera uma imagem mais clara do que
a mesma sala com a luz apagada. Medimos o brilho médio do frame usando o canal
V (Value) do espaço de cor HSV, que vai de 0 (preto) a 255 (máximo brilho).

Comparando esse valor com um limiar (calibrado para cada sala com o script
calibrar.py), decidimos se a luz está acesa ou apagada.
"""

from __future__ import annotations

import cv2
import numpy as np


def recortar_roi(frame: np.ndarray, roi: tuple[int, int, int, int] | None) -> np.ndarray:
    """Recorta a Região de Interesse (x, y, largura, altura).

    Usar uma ROI ajuda a ignorar janelas (luz do sol) e focar no teto ou
    numa parede que só fica clara quando as lâmpadas estão ligadas.
    """
    if roi is None:
        return frame
    x, y, w, h = roi
    altura, largura = frame.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(largura, x + w), min(altura, y + h)
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"ROI {roi} fica fora da imagem ({largura}x{altura})")
    return frame[y0:y1, x0:x1]


def calcular_brilho(frame: np.ndarray, roi: tuple[int, int, int, int] | None = None) -> float:
    """Retorna o brilho médio (0-255) do frame (ou da ROI)."""
    regiao = recortar_roi(frame, roi)
    if regiao.ndim == 2:  # já está em tons de cinza
        return float(regiao.mean())
    hsv = cv2.cvtColor(regiao, cv2.COLOR_BGR2HSV)
    return float(hsv[:, :, 2].mean())


class DetectorLuz:
    """Decide se a luz está acesa a partir do brilho, com histerese.

    A histerese evita que o estado fique "piscando" quando o brilho está bem
    perto do limiar (ex.: alguém passando na frente da câmera):
      - só considera ACESA quando brilho >= limiar + margem
      - só considera APAGADA quando brilho <= limiar - margem
      - entre os dois, mantém o estado anterior
    """

    def __init__(self, limiar: float = 100.0, margem: float = 5.0):
        self.limiar = limiar
        self.margem = margem
        self.acesa: bool | None = None

    def atualizar(self, brilho: float) -> bool:
        if self.acesa is None:
            self.acesa = brilho >= self.limiar
        elif brilho >= self.limiar + self.margem:
            self.acesa = True
        elif brilho <= self.limiar - self.margem:
            self.acesa = False
        return self.acesa
