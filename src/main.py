"""
Salas vazias com luz acesa - protótipo de visão computacional.

Lê uma webcam, câmera IP, arquivo de vídeo ou imagem e, a cada frame:
  1. detecta pessoas com YOLO;
  2. mede o brilho do ambiente para saber se a luz está acesa;
  3. atualiza a máquina de estados da sala;
  4. gera alerta quando a sala fica vazia com a luz acesa além da tolerância.

Exemplos:
  python src/main.py --fonte 0                         # webcam
  python src/main.py --fonte videos_teste/demo.mp4     # vídeo gravado
  python src/main.py --fonte foto_sala.jpg             # uma imagem
  python src/main.py --fonte 0 --sala "Sala 214-B" --limiar 95 --tolerancia 15
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2

from alerta import Registrador
from brilho import DetectorLuz, calcular_brilho
from detector import DetectorPessoas
from estado import MonitorSala
from visual import desenhar

EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def ler_roi(texto: str | None):
    if not texto:
        return None
    partes = [int(v) for v in texto.split(",")]
    if len(partes) != 4:
        raise argparse.ArgumentTypeError("ROI deve ser x,y,largura,altura (ex.: 0,0,640,120)")
    return tuple(partes)


def criar_argumentos() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Detecta salas vazias com a luz acesa.")
    p.add_argument("--fonte", default="0",
                   help="0/1 = webcam, caminho de vídeo/imagem ou URL rtsp:// (padrão: 0)")
    p.add_argument("--sala", default="Sala 01", help="Nome da sala (aparece na tela e no CSV)")
    p.add_argument("--limiar", type=float, default=100.0,
                   help="Brilho (0-255) a partir do qual a luz é considerada acesa. "
                        "Use calibrar.py para descobrir o valor da sua sala.")
    p.add_argument("--margem", type=float, default=5.0, help="Histerese do limiar de brilho")
    p.add_argument("--roi", type=ler_roi, default=None,
                   help="Região para medir o brilho: x,y,largura,altura (ex.: teto)")
    p.add_argument("--tolerancia", type=float, default=10.0,
                   help="Segundos com a sala vazia e acesa antes de alertar (padrão: 10)")
    p.add_argument("--modelo", default="yolov8n.pt", help="Modelo YOLO (padrão: yolov8n.pt)")
    p.add_argument("--confianca", type=float, default=0.4, help="Confiança mínima da detecção")
    p.add_argument("--intervalo", type=int, default=1,
                   help="Roda o YOLO a cada N frames (aumenta o FPS em PCs mais fracos)")
    p.add_argument("--potencia", type=float, default=216.0,
                   help="Potência total da iluminação da sala em W (padrão: 216 = 12 x 18 W)")
    p.add_argument("--tarifa", type=float, default=0.80, help="Tarifa de energia em R$/kWh")
    p.add_argument("--saida", default="data", help="Pasta para o CSV e as fotos dos alertas")
    p.add_argument("--salvar-video", default=None, help="Grava o vídeo anotado (ex.: saida.mp4)")
    p.add_argument("--sem-janela", action="store_true",
                   help="Não abre janela (útil em servidor / sem monitor)")
    return p


def abrir_fonte(fonte: str):
    if fonte.isdigit():
        return cv2.VideoCapture(int(fonte)), False
    if Path(fonte).suffix.lower() in EXTENSOES_IMAGEM:
        return None, False
    if not fonte.startswith(("rtsp://", "http://", "https://")) and not Path(fonte).exists():
        sys.exit(f"Arquivo não encontrado: {fonte}")
    return cv2.VideoCapture(fonte), not fonte.startswith(("rtsp://", "http://", "https://"))


def processar_imagem(args, detector: DetectorPessoas) -> None:
    frame = cv2.imread(args.fonte)
    if frame is None:
        sys.exit(f"Não foi possível abrir a imagem: {args.fonte}")

    deteccoes = detector.detectar(frame)
    brilho = calcular_brilho(frame, args.roi)
    luz = DetectorLuz(args.limiar, args.margem).atualizar(brilho)
    monitor = MonitorSala(args.sala, tolerancia_s=0)  # imagem: diagnóstico imediato
    monitor.atualizar(len(deteccoes) > 0, luz, 0.0)

    print(f"Pessoas: {len(deteccoes)} | Brilho: {brilho:.1f} | Luz: "
          f"{'ACESA' if luz else 'APAGADA'} | Estado: {monitor.estado.value}")

    anotado = desenhar(frame, sala=args.sala, estado=monitor.estado, deteccoes=deteccoes,
                       brilho=brilho, limiar=args.limiar, luz_acesa=luz,
                       tempo_vazia_acesa=0, tolerancia=0, qtd_alertas=monitor.qtd_alertas,
                       roi=args.roi)
    Path(args.saida).mkdir(parents=True, exist_ok=True)
    destino = Path(args.saida) / f"resultado_{Path(args.fonte).stem}.jpg"
    cv2.imwrite(str(destino), anotado)
    print(f"Imagem anotada salva em: {destino}")
    if not args.sem_janela:
        cv2.imshow("Salas vazias com luz acesa", anotado)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def processar_video(args, detector: DetectorPessoas) -> None:
    captura, eh_arquivo = abrir_fonte(args.fonte)
    if captura is None or not captura.isOpened():
        sys.exit(f"Não foi possível abrir a fonte de vídeo: {args.fonte}")

    fps_video = captura.get(cv2.CAP_PROP_FPS) or 30.0
    if fps_video <= 0 or fps_video > 240:
        fps_video = 30.0

    monitor = MonitorSala(args.sala, tolerancia_s=args.tolerancia)
    luz_detector = DetectorLuz(args.limiar, args.margem)
    registrador = Registrador(Path(args.saida), args.potencia, args.tarifa,
                              inicio_real=datetime.now())

    gravador = None
    indice = 0
    deteccoes = []
    inicio = time.monotonic()
    ultimo_tick, fps_medido = inicio, None
    agora = 0.0

    print(f"Monitorando '{args.sala}' (fonte: {args.fonte}). Pressione Q para sair.")
    try:
        while True:
            ok, frame = captura.read()
            if not ok:
                break

            # Em vídeo gravado, o tempo é a posição no vídeo; ao vivo, o relógio.
            agora = indice / fps_video if eh_arquivo else time.monotonic() - inicio

            if indice % args.intervalo == 0:
                deteccoes = detector.detectar(frame)
            brilho = calcular_brilho(frame, args.roi)
            luz_acesa = luz_detector.atualizar(brilho)

            eventos = monitor.atualizar(len(deteccoes) > 0, luz_acesa, agora)

            tick = time.monotonic()
            instantaneo = 1.0 / max(tick - ultimo_tick, 1e-6)
            fps_medido = instantaneo if fps_medido is None else 0.9 * fps_medido + 0.1 * instantaneo
            ultimo_tick = tick

            anotado = desenhar(frame, sala=args.sala, estado=monitor.estado, deteccoes=deteccoes,
                               brilho=brilho, limiar=args.limiar, luz_acesa=luz_acesa,
                               tempo_vazia_acesa=monitor.tempo_vazia_acesa_atual(agora),
                               tolerancia=args.tolerancia, qtd_alertas=monitor.qtd_alertas,
                               roi=args.roi, fps=fps_medido)

            for evento in eventos:
                registrador.registrar(evento, anotado)

            if args.salvar_video:
                if gravador is None:
                    h, w = anotado.shape[:2]
                    gravador = cv2.VideoWriter(args.salvar_video,
                                               cv2.VideoWriter_fourcc(*"mp4v"), fps_video, (w, h))
                gravador.write(anotado)

            if not args.sem_janela:
                cv2.imshow("Salas vazias com luz acesa", anotado)
                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):
                    break
            indice += 1
    except KeyboardInterrupt:
        pass
    finally:
        for evento in monitor.finalizar(agora):
            registrador.registrar(evento)
        captura.release()
        if gravador is not None:
            gravador.release()
        if not args.sem_janela:
            cv2.destroyAllWindows()

    print(registrador.resumo(args.sala, monitor.qtd_alertas,
                             monitor.tempo_total_desperdicio_s, agora))
    if args.salvar_video:
        print(f"Vídeo anotado salvo em: {args.salvar_video}")


def main() -> None:
    args = criar_argumentos().parse_args()
    if args.intervalo < 1:
        sys.exit("--intervalo deve ser 1 ou maior")

    print(f"Carregando modelo {args.modelo}...")
    detector = DetectorPessoas(args.modelo, args.confianca)

    if Path(args.fonte).suffix.lower() in EXTENSOES_IMAGEM:
        processar_imagem(args, detector)
    else:
        processar_video(args, detector)


if __name__ == "__main__":
    main()
