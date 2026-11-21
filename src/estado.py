"""
Máquina de estados da sala.

Junta as duas informações que a câmera fornece (tem pessoas? luz acesa?) e
decide o estado da sala ao longo do tempo:

    OCUPADA      -> há pessoas na sala (luz acesa ou não, tudo normal)
    APAGADA      -> sala vazia e luz apagada (situação ideal)
    VERIFICANDO  -> sala vazia com luz acesa, mas há pouco tempo
                    (pode ser alguém que saiu por um instante ou o detector
                    perdeu a pessoa por alguns frames)
    ALERTA       -> sala vazia com luz acesa há mais tempo que a tolerância:
                    desperdício confirmado, avisa a zeladoria

O tempo de tolerância evita alarmes falsos. Para a demonstração usamos poucos
segundos; numa instalação real faria sentido algo como 5 a 10 minutos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Estado(str, Enum):
    OCUPADA = "OCUPADA"
    APAGADA = "APAGADA"
    VERIFICANDO = "VERIFICANDO"
    ALERTA = "ALERTA"


@dataclass
class Evento:
    tipo: str             # "ALERTA_INICIO" ou "ALERTA_FIM"
    tempo: float          # instante (segundos) em que o evento aconteceu
    sala: str
    motivo: str = ""
    desperdicio_s: float = 0.0  # quanto tempo a sala ficou vazia e acesa


@dataclass
class MonitorSala:
    sala: str = "Sala"
    tolerancia_s: float = 10.0

    estado: Estado | None = None
    inicio_vazia_acesa: float | None = None
    tempo_total_desperdicio_s: float = 0.0
    qtd_alertas: int = 0
    eventos: list[Evento] = field(default_factory=list)

    def atualizar(self, tem_pessoas: bool, luz_acesa: bool, agora: float) -> list[Evento]:
        """Processa uma nova leitura e devolve os eventos gerados nela."""
        novos: list[Evento] = []
        vazia_e_acesa = (not tem_pessoas) and luz_acesa

        if vazia_e_acesa:
            if self.inicio_vazia_acesa is None:
                self.inicio_vazia_acesa = agora
            tempo_assim = agora - self.inicio_vazia_acesa

            if tempo_assim >= self.tolerancia_s:
                if self.estado != Estado.ALERTA:
                    self.qtd_alertas += 1
                    novos.append(Evento("ALERTA_INICIO", agora, self.sala,
                                        "Sala vazia com a luz acesa", tempo_assim))
                self.estado = Estado.ALERTA
            else:
                self.estado = Estado.VERIFICANDO
        else:
            # Saiu da condição "vazia e acesa": fecha o período de desperdício.
            if self.inicio_vazia_acesa is not None:
                duracao = agora - self.inicio_vazia_acesa
                if self.estado == Estado.ALERTA:
                    motivo = "Pessoa entrou na sala" if tem_pessoas else "Luz foi apagada"
                    novos.append(Evento("ALERTA_FIM", agora, self.sala, motivo, duracao))
                    self.tempo_total_desperdicio_s += duracao
                self.inicio_vazia_acesa = None
            self.estado = Estado.OCUPADA if tem_pessoas else Estado.APAGADA

        self.eventos.extend(novos)
        return novos

    def finalizar(self, agora: float) -> list[Evento]:
        """Fecha um alerta em aberto quando o vídeo/câmera termina."""
        novos: list[Evento] = []
        if self.estado == Estado.ALERTA and self.inicio_vazia_acesa is not None:
            duracao = agora - self.inicio_vazia_acesa
            novos.append(Evento("ALERTA_FIM", agora, self.sala,
                                "Monitoramento encerrado", duracao))
            self.tempo_total_desperdicio_s += duracao
            self.inicio_vazia_acesa = None
        self.eventos.extend(novos)
        return novos

    def tempo_vazia_acesa_atual(self, agora: float) -> float:
        if self.inicio_vazia_acesa is None:
            return 0.0
        return agora - self.inicio_vazia_acesa
