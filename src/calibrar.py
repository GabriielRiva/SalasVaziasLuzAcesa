"""
Calibração do limiar de brilho.

Cada sala (e cada posição de câmera) tem um brilho diferente, então o limiar
que separa "luz acesa" de "luz apagada" precisa ser medido no local.

Como usar (com janela):
  python src/calibrar.py --fonte 0
    - deixe a luz ACESA e segure a tecla A por alguns segundos;
    - apague a luz e segure a tecla P por alguns segundos;
    - pressione Q: o script sugere o limiar (ponto médio entre os dois).

Sem janela (vídeos gravados com a luz acesa e apagada):
  python src/calibrar.py --acesa videos_teste/luz_acesa.mp4 --apagada videos_teste/luz_apagada.mp4
"""

from __future__ import annotations

import argparse
import statistics
import sys

import cv2

from brilho import calcular_brilho
from main import ler_roi


def brilhos_do_video(caminho: str, roi) -> list[float]:
    captura = cv2.VideoCapture(caminho)
    if not captura.isOpened():
        sys.exit(f"Não foi possível abrir: {caminho}")
    valores = []
    while True:
        ok, frame = captura.read()
        if not ok:
            break
        valores.append(calcular_brilho(frame, roi))
    captura.release()
    if not valores:
        sys.exit(f"Nenhum frame lido de: {caminho}")
    return valores


def sugerir(acesa: list[float], apagada: list[float]) -> None:
    media_acesa, media_apagada = statistics.mean(acesa), statistics.mean(apagada)
    print(f"\nLuz ACESA   -> brilho médio {media_acesa:6.1f} (mín {min(acesa):.1f}, máx {max(acesa):.1f})")
    print(f"Luz APAGADA -> brilho médio {media_apagada:6.1f} (mín {min(apagada):.1f}, máx {max(apagada):.1f})")
    if min(acesa) <= max(apagada):
        print("\nATENÇÃO: os valores se sobrepõem. Tente usar --roi numa área que só é "
              "iluminada pelas lâmpadas (ex.: teto), longe de janelas.")
    limiar = (min(acesa) + max(apagada)) / 2
    margem = min(15.0, max(2.0, (min(acesa) - max(apagada)) / 4))
    print(f"\nLimiar sugerido: --limiar {limiar:.0f} --margem {margem:.0f}")


def modo_interativo(fonte: str, roi) -> None:
    captura = cv2.VideoCapture(int(fonte) if fonte.isdigit() else fonte)
    if not captura.isOpened():
        sys.exit(f"Não foi possível abrir a fonte: {fonte}")
    acesa, apagada = [], []
    print("Segure A com a luz ACESA, P com a luz APAGADA, Q para terminar.")
    while True:
        ok, frame = captura.read()
        if not ok:
            break
        brilho = calcular_brilho(frame, roi)
        texto = f"Brilho: {brilho:.1f} | amostras acesa={len(acesa)} apagada={len(apagada)}"
        cv2.putText(frame, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
        cv2.putText(frame, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        if roi:
            x, y, w, h = roi
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 200, 255), 2)
        cv2.imshow("Calibracao de brilho", frame)
        tecla = cv2.waitKey(30) & 0xFF
        if tecla in (ord("a"), ord("A")):
            acesa.append(brilho)
        elif tecla in (ord("p"), ord("P")):
            apagada.append(brilho)
        elif tecla in (ord("q"), ord("Q"), 27):
            break
    captura.release()
    cv2.destroyAllWindows()
    if acesa and apagada:
        sugerir(acesa, apagada)
    else:
        print("Faltaram amostras: colete com a luz acesa (A) e apagada (P).")


def main() -> None:
    p = argparse.ArgumentParser(description="Calibra o limiar de brilho da sala.")
    p.add_argument("--fonte", default="0", help="Webcam (0) ou vídeo para o modo interativo")
    p.add_argument("--acesa", help="Vídeo gravado com a luz acesa")
    p.add_argument("--apagada", help="Vídeo gravado com a luz apagada")
    p.add_argument("--roi", type=ler_roi, default=None, help="x,y,largura,altura")
    args = p.parse_args()

    if args.acesa and args.apagada:
        sugerir(brilhos_do_video(args.acesa, args.roi), brilhos_do_video(args.apagada, args.roi))
    else:
        modo_interativo(args.fonte, args.roi)


if __name__ == "__main__":
    main()
