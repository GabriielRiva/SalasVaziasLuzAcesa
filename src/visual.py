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
    # Tudo é proporcional à largura do vídeo (referência: 1280 px). Assim, depois que a
    # janela redimensiona o frame para a largura fixa, o texto tem sempre o mesmo tamanho.
    esc = largura / 1280

    def px(v: float) -> int:
        return max(1, round(v * esc))

    # Caixas das pessoas detectadas
    for d in deteccoes:
        cv2.rectangle(img, (d.x1, d.y1), (d.x2, d.y2), VERDE, px(2))
        _texto(img, f"pessoa {d.confianca:.0%}", (d.x1, max(px(15), d.y1 - px(6))),
               0.5 * esc, VERDE, px(1))

    # Faixa superior com o estado
    cv2.rectangle(img, (0, 0), (largura, px(42)), cor, -1)
    _texto(img, f"{sala} | {TEXTO_ESTADO[estado]}", (px(10), px(28)), 0.7 * esc, BRANCO, px(2))

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

    x0, y0 = px(10), px(55)
    altura_painel = px(22) * len(linhas) + px(10)
    sobreposicao = img.copy()
    cv2.rectangle(sobreposicao, (x0 - px(5), y0 - px(5)),
                  (x0 + px(540), y0 + altura_painel), PRETO, -1)
    img = cv2.addWeighted(sobreposicao, 0.45, img, 0.55, 0)
    for i, linha in enumerate(linhas):
        _texto(img, linha, (x0, y0 + px(18) + px(22) * i), 0.55 * esc, BRANCO, px(1))

    # Região usada para medir o brilho
    if roi is not None:
        x, y, w, h = roi
        cv2.rectangle(img, (x, y), (x + w, y + h), AMARELO, px(1))
        _texto(img, "ROI brilho", (x + px(4), y + h - px(6)), 0.45 * esc, AMARELO, px(1))

    # Borda vermelha durante o alerta
    if estado == Estado.ALERTA:
        cv2.rectangle(img, (0, 0), (largura - 1, altura - 1), VERMELHO, px(8))

    return img


def desenhar_resumo(frame: np.ndarray, *, sala: str, tempo_monitorado: float, qtd_alertas: int,
                    desperdicio_s: float, kwh: float, custo: float,
                    potencia_w: float) -> np.ndarray:
    """Tela final: o último frame escurecido com o resumo do monitoramento no centro."""
    img = (frame * 0.35).astype(np.uint8)
    altura, largura = img.shape[:2]
    perc = desperdicio_s / tempo_monitorado * 100 if tempo_monitorado > 0 else 0.0
    cor_titulo = VERMELHO if qtd_alertas > 0 else VERDE
    esc = largura / 1280  # escala proporcional à resolução

    linhas = [
        ("Sala", sala),
        ("Tempo monitorado", formatar_duracao(tempo_monitorado)),
        ("Alertas gerados", str(qtd_alertas)),
        ("Vazia com luz acesa", f"{formatar_duracao(desperdicio_s)} ({perc:.0f}%)"),
        ("Energia desperdicada", f"{kwh:.4f} kWh ({potencia_w:.0f} W)"),
        ("Custo estimado", f"R$ {custo:.4f}"),
    ]
    pw, ph = int(760 * esc), int(430 * esc)
    x0, y0 = (largura - pw) // 2, (altura - ph) // 2
    cv2.rectangle(img, (x0, y0), (x0 + pw, y0 + ph), (45, 42, 40), -1)
    cv2.rectangle(img, (x0, y0), (x0 + pw, y0 + int(60 * esc)), cor_titulo, -1)
    _texto(img, "RESUMO DO MONITORAMENTO", (x0 + int(24 * esc), y0 + int(40 * esc)),
           1.0 * esc, BRANCO, 2)
    for i, (rotulo, valor) in enumerate(linhas):
        y = y0 + int((115 + i * 52) * esc)
        _texto(img, rotulo, (x0 + int(30 * esc), y), 0.8 * esc, (190, 190, 190), 1)
        _texto(img, valor, (x0 + int(330 * esc), y), 0.85 * esc, BRANCO, 2)
    _texto(img, "Pressione qualquer tecla para fechar",
           (x0 + int(30 * esc), y0 + ph - int(20 * esc)), 0.6 * esc, (170, 170, 170), 1)
    return img
