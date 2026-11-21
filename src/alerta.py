"""
Registro dos alertas e estimativa do desperdício.

Cada alerta é:
  - mostrado no terminal;
  - gravado no arquivo CSV de eventos (histórico para a zeladoria/gestão);
  - acompanhado de uma foto (snapshot) do momento, como evidência.

A estimativa de energia usa a potência total de iluminação da sala
(ex.: 12 lâmpadas LED tubulares de 18 W = 216 W) e a tarifa em R$/kWh.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np

from estado import Evento


def energia_kwh(duracao_s: float, potencia_w: float) -> float:
    return potencia_w * (duracao_s / 3600.0) / 1000.0


def formatar_duracao(segundos: float) -> str:
    segundos = int(round(segundos))
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class Registrador:
    CABECALHO = ["data_hora", "sala", "evento", "motivo", "tempo_vazia_acesa",
                 "energia_kwh", "custo_rs", "foto"]

    def __init__(self, pasta_saida: Path, potencia_w: float, tarifa_rs_kwh: float,
                 inicio_real: datetime | None = None):
        self.pasta_saida = Path(pasta_saida)
        self.pasta_fotos = self.pasta_saida / "alertas"
        self.pasta_fotos.mkdir(parents=True, exist_ok=True)
        self.arquivo_csv = self.pasta_saida / "eventos.csv"
        self.potencia_w = potencia_w
        self.tarifa = tarifa_rs_kwh
        # Para vídeos gravados, o "tempo" é a posição no vídeo; somamos ao
        # horário de início para ter um data/hora legível no CSV.
        self.inicio_real = inicio_real or datetime.now()

        if not self.arquivo_csv.exists():
            with open(self.arquivo_csv, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(self.CABECALHO)

    def registrar(self, evento: Evento, frame: np.ndarray | None = None) -> None:
        data_hora = self.inicio_real + timedelta(seconds=evento.tempo)
        kwh = energia_kwh(evento.desperdicio_s, self.potencia_w)
        custo = kwh * self.tarifa

        foto = ""
        if frame is not None and evento.tipo == "ALERTA_INICIO":
            nome = f"{evento.sala}_{data_hora:%Y%m%d_%H%M%S}.jpg".replace(" ", "_")
            caminho = self.pasta_fotos / nome
            cv2.imwrite(str(caminho), frame)
            foto = str(caminho)

        with open(self.arquivo_csv, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                f"{data_hora:%Y-%m-%d %H:%M:%S}", evento.sala, evento.tipo, evento.motivo,
                formatar_duracao(evento.desperdicio_s), f"{kwh:.4f}", f"{custo:.4f}", foto,
            ])

        if evento.tipo == "ALERTA_INICIO":
            print(f"[{data_hora:%H:%M:%S}] *** ALERTA *** {evento.sala}: {evento.motivo} "
                  f"(há {formatar_duracao(evento.desperdicio_s)})")
        else:
            print(f"[{data_hora:%H:%M:%S}] Alerta encerrado em {evento.sala}: {evento.motivo}. "
                  f"Tempo vazia e acesa: {formatar_duracao(evento.desperdicio_s)} "
                  f"| {kwh:.4f} kWh | R$ {custo:.4f}")

    def resumo(self, sala: str, qtd_alertas: int, desperdicio_s: float,
               tempo_monitorado_s: float) -> str:
        kwh = energia_kwh(desperdicio_s, self.potencia_w)
        perc = (desperdicio_s / tempo_monitorado_s * 100) if tempo_monitorado_s > 0 else 0
        return (
            "\n================ RESUMO DO MONITORAMENTO ================\n"
            f"Sala ......................: {sala}\n"
            f"Tempo monitorado ..........: {formatar_duracao(tempo_monitorado_s)}\n"
            f"Alertas gerados ...........: {qtd_alertas}\n"
            f"Tempo vazia com luz acesa .: {formatar_duracao(desperdicio_s)} ({perc:.1f}%)\n"
            f"Energia desperdiçada ......: {kwh:.4f} kWh "
            f"(potência considerada: {self.potencia_w:.0f} W)\n"
            f"Custo estimado ............: R$ {kwh * self.tarifa:.4f} "
            f"(tarifa: R$ {self.tarifa:.2f}/kWh)\n"
            f"Histórico .................: {self.arquivo_csv}\n"
            "=========================================================="
        )
