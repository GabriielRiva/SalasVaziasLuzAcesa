"""
Detecção de pessoas com YOLO (Ultralytics).

Usamos um modelo pré-treinado no dataset COCO, que já reconhece 80 classes de
objetos. A classe 0 do COCO é "person", então filtramos só ela. Não é preciso
treinar nada: o modelo é baixado automaticamente na primeira execução.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

CLASSE_PESSOA = 0  # índice de "person" no COCO


@dataclass
class Deteccao:
    x1: int
    y1: int
    x2: int
    y2: int
    confianca: float


class DetectorPessoas:
    def __init__(self, modelo: str = "yolov8n.pt", confianca_minima: float = 0.4,
                 tamanho_imagem: int = 640):
        # Import aqui dentro para que os outros módulos (brilho, estado) possam
        # ser usados/testados sem precisar instalar o PyTorch.
        from ultralytics import YOLO

        self.modelo = YOLO(modelo)
        self.confianca_minima = confianca_minima
        self.tamanho_imagem = tamanho_imagem

    def detectar(self, frame: np.ndarray) -> list[Deteccao]:
        resultado = self.modelo.predict(
            frame,
            classes=[CLASSE_PESSOA],
            conf=self.confianca_minima,
            imgsz=self.tamanho_imagem,
            verbose=False,
        )[0]

        deteccoes = []
        for caixa in resultado.boxes:
            x1, y1, x2, y2 = (int(v) for v in caixa.xyxy[0].tolist())
            deteccoes.append(Deteccao(x1, y1, x2, y2, float(caixa.conf[0])))
        return deteccoes
