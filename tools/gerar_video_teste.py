"""
Gera um vídeo SINTÉTICO de teste, para validar o sistema sem câmera.

Desenha uma "sala de aula" simples com pessoas ilustradas e encena:
   0-10 s  luz acesa, duas pessoas na sala   -> OCUPADA
  10-28 s  pessoas saem, luz fica acesa      -> VERIFICANDO e depois ALERTA
  28-34 s  uma pessoa volta                  -> fim do alerta (pessoa entrou)
  34-48 s  sala vazia de novo, luz acesa     -> novo ALERTA
  48-58 s  alguém apaga a luz                -> fim do alerta (luz apagada)

Este vídeo serve só para testar o código. Para a apresentação do trabalho,
gravem um vídeo REAL numa sala da Unochapecó.

Uso:
  python tools/gerar_video_teste.py --saida videos_teste/demo_sintetico.mp4
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

LARGURA, ALTURA, FPS = 960, 540, 15
AA = cv2.LINE_AA


def desenhar_sala() -> np.ndarray:
    sala = np.full((ALTURA, LARGURA, 3), (205, 215, 220), np.uint8)       # parede
    cv2.rectangle(sala, (0, 380), (LARGURA, ALTURA), (150, 165, 175), -1)   # piso
    cv2.rectangle(sala, (300, 70), (700, 250), (60, 90, 50), -1)            # quadro
    cv2.rectangle(sala, (300, 70), (700, 250), (90, 90, 90), 6)
    for i in range(4):                                                      # lâmpadas
        cv2.rectangle(sala, (110 + i * 210, 15), (230 + i * 210, 30), (250, 250, 250), -1)
    for linha in range(2):                                                  # carteiras
        for col in range(5):
            x, y = 90 + col * 170, 400 + linha * 70
            cv2.rectangle(sala, (x, y), (x + 110, y + 18), (70, 110, 150), -1)
            cv2.line(sala, (x + 10, y + 18), (x + 10, y + 55), (60, 60, 60), 4)
            cv2.line(sala, (x + 100, y + 18), (x + 100, y + 55), (60, 60, 60), 4)
    return sala


def desenhar_pessoa(altura: int, camisa, calca=(60, 50, 40), pele=(150, 180, 215),
                    cabelo=(30, 30, 40)):
    """Desenha uma pessoa simples. Devolve (imagem, máscara)."""
    h, w = altura, int(altura * 0.42)
    img = np.zeros((h, w, 3), np.uint8)
    mask = np.zeros((h, w), np.uint8)
    cx, r = w // 2, int(h * 0.075)

    def poligono(pts, cor):
        pts = np.array(pts, np.int32)
        cv2.fillPoly(img, [pts], cor, AA)
        cv2.fillPoly(mask, [pts], 255)

    def elipse(centro, eixos, cor, ini=0, fim=360):
        cv2.ellipse(img, centro, eixos, 0, ini, fim, cor, -1, AA)
        cv2.ellipse(mask, centro, eixos, 0, ini, fim, 255, -1)

    def ret(p1, p2, cor):
        cv2.rectangle(img, p1, p2, cor, -1)
        cv2.rectangle(mask, p1, p2, 255, -1)

    # pernas e sapatos
    ret((cx - int(w * .22), int(h * .52)), (cx - int(w * .03), int(h * .96)), calca)
    ret((cx + int(w * .03), int(h * .52)), (cx + int(w * .22), int(h * .96)), calca)
    for s in (-1, 1):
        elipse((cx + s * int(w * .14), int(h * .97)), (int(w * .13), int(h * .025)), (20, 20, 20))
    # tronco
    poligono([(cx - int(w * .3), int(h * .2)), (cx + int(w * .3), int(h * .2)),
              (cx + int(w * .25), int(h * .55)), (cx - int(w * .25), int(h * .55))], camisa)
    # braços e mãos
    for s in (-1, 1):
        poligono([(cx + s * int(w * .3), int(h * .2)), (cx + s * int(w * .45), int(h * .45)),
                  (cx + s * int(w * .38), int(h * .47)), (cx + s * int(w * .24), int(h * .27))], camisa)
        elipse((cx + s * int(w * .42), int(h * .49)), (int(w * .06), int(w * .06)), pele)
    # pescoço, cabeça, cabelo e olhos
    ret((cx - int(r * .4), int(h * .15)), (cx + int(r * .4), int(h * .21)), pele)
    elipse((cx, int(h * .1)), (int(r * .85), r), pele)
    cv2.ellipse(img, (cx, int(h * .08)), (int(r * .9), int(r * .75)), 0, 180, 360, cabelo, -1, AA)
    for s in (-1, 1):
        cv2.circle(img, (cx + s * int(r * .3), int(h * .1)), 3, (30, 30, 30), -1)
    return img, mask


def colar(fundo: np.ndarray, pessoa, x: int) -> None:
    img, mask = pessoa
    h, w = img.shape[:2]
    y = ALTURA - h - 15
    x = max(0, min(LARGURA - w, int(x)))
    regiao = fundo[y:y + h, x:x + w]
    regiao[mask > 0] = img[mask > 0]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--saida", default="videos_teste/demo_sintetico.mp4")
    args = p.parse_args()
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)

    sala_acesa = desenhar_sala()
    sala_apagada = (sala_acesa * 0.22).astype(np.uint8)
    azul = desenhar_pessoa(340, camisa=(160, 80, 40))
    vermelho = desenhar_pessoa(340, camisa=(50, 60, 170))
    ruido = np.random.default_rng(42)

    # (segundos, luz acesa?, [(pessoa, x_inicial, x_final), ...])
    roteiro = [
        (10, True, [(azul, 120, 160), (vermelho, 600, 560)]),
        (18, True, []),
        (6, True, [(vermelho, -50, 380)]),
        (14, True, []),
        (10, False, []),
    ]

    gravador = cv2.VideoWriter(args.saida, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (LARGURA, ALTURA))
    for duracao, acesa, pessoas in roteiro:
        total = int(duracao * FPS)
        for i in range(total):
            frame = (sala_acesa if acesa else sala_apagada).copy()
            for pessoa, x0, x1 in pessoas:
                colar(frame, pessoa, x0 + (x1 - x0) * min(1.0, i / (total * 0.5)))
            # ruído leve, como o de uma câmera real
            frame = np.clip(frame.astype(np.int16) + ruido.integers(-6, 7, frame.shape), 0, 255)
            gravador.write(frame.astype(np.uint8))
    gravador.release()
    print(f"Vídeo de teste salvo em {args.saida} ({sum(r[0] for r in roteiro)} s)")


if __name__ == "__main__":
    main()
