"""
Desenho das informações sobre o frame (o que aparece na tela da demonstração).

Obs.: o cv2.putText não desenha acentos, por isso os textos na imagem estão
sem acentuação.
"""

from __future__ import annotations

import cv2
import numpy as np

from alerta import formatar_duracao
from detector import Deteccao
from estado import Estado

# Cores em BGR
VERDE = (60, 180, 75)
CINZA = (128, 128, 128)
AMARELO = (0, 200, 255)
VERMELHO = (40, 40, 220)
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)

COR_ESTADO = {
    Estado.OCUPADA: VERDE,
    Estado.APAGADA: CINZA,
    Estado.VERIFICANDO: AMARELO,
    Estado.ALERTA: VERMELHO,
}

TEXTO_ESTADO = {
    Estado.OCUPADA: "SALA OCUPADA",
    Estado.APAGADA: "SALA VAZIA - LUZ APAGADA (OK)",
    Estado.VERIFICANDO: "SALA VAZIA COM LUZ ACESA - VERIFICANDO...",
    Estado.ALERTA: "ALERTA: SALA VAZIA COM LUZ ACESA!",
}


def _texto(img, texto, pos, escala=0.6, cor=BRANCO, espessura=1):
    # sombra deslocada (funciona igual no OpenCV 4 e 5)
    sombra = (pos[0] + 1, pos[1] + 1)
    cv2.putText(img, texto, sombra, cv2.FONT_HERSHEY_SIMPLEX, escala, PRETO, espessura, cv2.LINE_AA)
    cv2.putText(img, texto, pos, cv2.FONT_HERSHEY_SIMPLEX, escala, cor, espessura, cv2.LINE_AA)


def desenhar(frame: np.ndarray, *, sala: str, estado: Estado, deteccoes: list[Deteccao],
             brilho: float, limiar: float, luz_acesa: bool, tempo_vazia_acesa: float,
             tolerancia: float, qtd_alertas: int, roi: tuple[int, int, int, int] | None,
             fps: float | None = None) -> np.ndarray:
    img = frame.copy()
    altura, largura = img.shape[:2]
    cor = COR_ESTADO[estado]

    # Caixas das pessoas detectadas
    for d in deteccoes:
        cv2.rectangle(img, (d.x1, d.y1), (d.x2, d.y2), VERDE, 2)
        _texto(img, f"pessoa {d.confianca:.0%}", (d.x1, max(15, d.y1 - 6)), 0.5, VERDE)

    # Faixa superior com o estado
    cv2.rectangle(img, (0, 0), (largura, 42), cor, -1)
    _texto(img, f"{sala} | {TEXTO_ESTADO[estado]}", (10, 28), 0.7, BRANCO, 2)

    # Painel de informações
    linhas = [
        f"Pessoas detectadas: {len(deteccoes)}",
        f"Brilho: {brilho:5.1f}  (limiar {limiar:.0f})",
        f"Luz: {'ACESA' if luz_acesa else 'APAGADA'}",
        f"Vazia e acesa ha: {formatar_duracao(tempo_vazia_acesa)} (tolerancia {tolerancia:.0f}s)",
        f"Alertas: {qtd_alertas}",
    ]
    if fps is not None:
        linhas.append(f"FPS: {fps:.1f}")

    x0, y0 = 10, 55
    altura_painel = 22 * len(linhas) + 10
    sobreposicao = img.copy()
    cv2.rectangle(sobreposicao, (x0 - 5, y0 - 5), (x0 + 540, y0 + altura_painel), PRETO, -1)
    img = cv2.addWeighted(sobreposicao, 0.45, img, 0.55, 0)
    for i, linha in enumerate(linhas):
        _texto(img, linha, (x0, y0 + 18 + 22 * i), 0.55)

    # Região usada para medir o brilho
    if roi is not None:
        x, y, w, h = roi
        cv2.rectangle(img, (x, y), (x + w, y + h), AMARELO, 1)
        _texto(img, "ROI brilho", (x + 4, y + h - 6), 0.45, AMARELO)

    # Borda vermelha durante o alerta
    if estado == Estado.ALERTA:
        cv2.rectangle(img, (0, 0), (largura - 1, altura - 1), VERMELHO, 8)

    return img
