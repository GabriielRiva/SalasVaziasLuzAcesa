"""Menu para escolher qual vídeo monitorar.

Mostra uma grade com a miniatura de cada vídeo da pasta (padrão: salasdeaula/).
Dê DOIS CLIQUES em um vídeo para abrir a janela de monitoramento dele.
Ao fechar o monitoramento (Q), o menu volta. Q ou ESC no menu encerra.

    python src/launcher.py
    python src/launcher.py --pasta salasdeaula --tolerancia 5

Qualquer opção desconhecida (ex.: --tolerancia, --limiar, --roi) é repassada ao main.py.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
EXTENSOES = {".mp4", ".avi", ".mov", ".mkv", ".m4v", ".wmv"}
JANELA = "Salas vazias com luz acesa - escolha um video"

COLUNAS = 3
MINI_W, MINI_H = 360, 203          # miniatura 16:9
MARGEM = 20
TITULO_H = 28
CABECALHO_H = 70
CARD_W = MINI_W
CARD_H = MINI_H + TITULO_H
INTERVALO_DUPLO_CLIQUE = 0.6       # segundos entre os dois cliques

FUNDO = (40, 36, 33)
CARD = (66, 60, 56)
DESTAQUE = (80, 200, 120)
TEXTO = (240, 240, 240)
TEXTO_FRACO = (170, 170, 170)


def listar_videos(pasta: Path) -> list[Path]:
    return sorted(p for p in pasta.iterdir() if p.suffix.lower() in EXTENSOES)


def miniatura(video: Path) -> np.ndarray:
    """Frame do meio do vídeo, no tamanho da miniatura (ou um quadro cinza se falhar)."""
    captura = cv2.VideoCapture(str(video))
    frame = None
    total = int(captura.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total > 1:
        captura.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
    ok, lido = captura.read()
    if ok:
        frame = lido
    captura.release()
    if frame is None:
        return np.full((MINI_H, MINI_W, 3), 90, np.uint8)
    return cv2.resize(frame, (MINI_W, MINI_H), interpolation=cv2.INTER_AREA)


def nome_amigavel(video: Path) -> str:
    return video.stem.replace("_", " ")


class Menu:
    def __init__(self, videos: list[Path]):
        self.videos = videos
        self.minis = [miniatura(v) for v in videos]
        linhas = max(1, -(-len(videos) // COLUNAS))
        colunas = min(COLUNAS, max(1, len(videos)))
        self.largura = MARGEM + colunas * (CARD_W + MARGEM)
        self.altura = CABECALHO_H + linhas * (CARD_H + MARGEM) + MARGEM
        self.selecionado: int | None = None
        self.ultimo_clique: tuple[int, float] | None = None
        self.escolhido: Path | None = None

    def retangulo(self, i: int) -> tuple[int, int, int, int]:
        linha, coluna = divmod(i, COLUNAS)
        x = MARGEM + coluna * (CARD_W + MARGEM)
        y = CABECALHO_H + linha * (CARD_H + MARGEM)
        return x, y, x + CARD_W, y + CARD_H

    def card_em(self, x: int, y: int) -> int | None:
        for i in range(len(self.videos)):
            x0, y0, x1, y1 = self.retangulo(i)
            if x0 <= x <= x1 and y0 <= y <= y1:
                return i
        return None

    def desenhar(self) -> np.ndarray:
        img = np.full((self.altura, self.largura, 3), FUNDO, np.uint8)
        cv2.putText(img, "Salas vazias com luz acesa", (MARGEM, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, TEXTO, 2, cv2.LINE_AA)
        cv2.putText(img, "Dois cliques em um video para monitorar  |  Q ou ESC para sair",
                    (MARGEM, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXTO_FRACO, 1, cv2.LINE_AA)
        if not self.videos:
            cv2.putText(img, "Nenhum video encontrado na pasta.", (MARGEM, CABECALHO_H + 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXTO, 1, cv2.LINE_AA)
        for i, video in enumerate(self.videos):
            x0, y0, x1, y1 = self.retangulo(i)
            cv2.rectangle(img, (x0, y0), (x1, y1), CARD, -1)
            img[y0:y0 + MINI_H, x0:x0 + MINI_W] = self.minis[i]
            cv2.putText(img, nome_amigavel(video)[:38], (x0 + 8, y0 + MINI_H + 19),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXTO, 1, cv2.LINE_AA)
            if i == self.selecionado:
                cv2.rectangle(img, (x0 - 3, y0 - 3), (x1 + 3, y1 + 3), DESTAQUE, 3)
        return img

    def ao_mouse(self, evento, x, y, _flags, _param) -> None:
        if evento != cv2.EVENT_LBUTTONDOWN:
            return
        i = self.card_em(x, y)
        if i is None:
            self.selecionado = None
            self.ultimo_clique = None
            return
        agora = time.monotonic()
        if (self.ultimo_clique and self.ultimo_clique[0] == i
                and agora - self.ultimo_clique[1] <= INTERVALO_DUPLO_CLIQUE):
            self.escolhido = self.videos[i]
            self.ultimo_clique = None
        else:
            self.ultimo_clique = (i, agora)
        self.selecionado = i


def abrir_monitoramento(video: Path, extras: list[str]) -> None:
    comando = [sys.executable, str(RAIZ / "src" / "main.py"),
               "--fonte", str(video), "--sala", nome_amigavel(video), *extras]
    print(f"\n>>> {' '.join(comando)}")
    subprocess.run(comando, cwd=RAIZ)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pasta", default="salasdeaula", help="Pasta com os vídeos (padrão: salasdeaula)")
    args, extras = p.parse_known_args()

    pasta = Path(args.pasta)
    if not pasta.is_absolute():
        pasta = RAIZ / pasta
    if not pasta.is_dir():
        sys.exit(f"Pasta não encontrada: {pasta}")

    menu = Menu(listar_videos(pasta))
    while True:
        cv2.namedWindow(JANELA, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(JANELA, menu.ao_mouse)
        while menu.escolhido is None:
            cv2.imshow(JANELA, menu.desenhar())
            tecla = cv2.waitKey(30) & 0xFF
            if tecla in (ord("q"), ord("Q"), 27):
                cv2.destroyAllWindows()
                return
            if cv2.getWindowProperty(JANELA, cv2.WND_PROP_VISIBLE) < 1:
                return
        video, menu.escolhido = menu.escolhido, None
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        abrir_monitoramento(video, extras)


if __name__ == "__main__":
    main()
