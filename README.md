# Salas vazias com luz acesa 💡

Protótipo de **visão computacional** que identifica, em tempo real, salas de aula e laboratórios **vazios com a luz acesa** e gera um alerta com foto, registro em histórico e estimativa da energia desperdiçada.

Trabalho do componente curricular **Robótica e Visão Computacional** do curso de Ciência da Computação da **Unochapecó**, com o professor Wagner Titon.

**Integrantes:** Alexandre Beilner, Gabriel Riva, João Pedro Pilatti, Leonardo Ribeiro e Matheus Eickhoff.

---

## 1. O problema

No campus de Chapecó da Unochapecó (146 salas e 139 laboratórios em 2022) é comum encontrar **salas vazias com a luz acesa**. A última pessoa sai sem apagar porque acha que outra turma vai usar a sala depois. A luz só é apagada quando a zeladoria ou a vigilância passa na ronda, o que pode levar horas.

- **Causas:** ninguém se sente responsável quando várias turmas usam a mesma sala, existe o hábito de acender ao chegar e esquecer ao sair, o interruptor é manual e a ronda demora.
- **Quem é afetado:** zeladoria, vigilância, infraestrutura e gestão. Alunos e professores também pagam esse custo.
- **Por que importa:** a iluminação representa cerca de 24% do consumo de energia em prédios públicos. Numa universidade parecida (UEM), 49 de 118 prédios tinham lâmpadas acesas sem necessidade.
- **Lacuna:** as soluções atuais (ronda, cartazes, sensor de presença, temporizador) **não mostram em tempo real** quais salas estão vazias e acesas. O sensor de presença ainda pode apagar a luz com um aluno parado na sala.

Os detalhes e as referências estão em [`docs/Etapa_1_Identificacao_do_Problema.pdf`](docs/Etapa_1_Identificacao_do_Problema.pdf).

## 2. A solução

Uma câmera consegue observar as duas coisas que importam ao mesmo tempo:

1. **Se tem gente na sala**, por meio da detecção de pessoas com YOLO.
2. **Se a luz está acesa**, por meio da análise do brilho da imagem.

O sistema combina essas duas informações numa **máquina de estados**. Quando a sala fica vazia com a luz acesa por mais tempo que a tolerância configurada, ele gera um **alerta**.

```
            ┌───────────────┐   pessoas = 0 e luz acesa   ┌──────────────┐
            │   OCUPADA     │ ──────────────────────────► │ VERIFICANDO  │
            │ (há pessoas)  │ ◄────────────────────────── │ (tolerância) │
            └───────────────┘       pessoa detectada      └──────┬───────┘
                    ▲                                            │ passou a tolerância
                    │ pessoa entrou                              ▼
            ┌───────┴───────┐         luz apagada         ┌──────────────┐
            │   APAGADA     │ ◄────────────────────────── │    ALERTA    │
            │ (vazia, ok)   │                             │ foto + CSV   │
            └───────────────┘                             └──────────────┘
```

A **tolerância** evita alarmes falsos, por exemplo quando alguém sai por um instante ou quando o detector perde a pessoa por alguns frames. Na demonstração usamos 10 s. Numa instalação real o valor seria algo entre 5 e 10 minutos.

### Funcionalidades

- Detecção de pessoas em tempo real (webcam, câmera IP/RTSP, vídeo gravado ou imagem).
- Detecção de luz acesa ou apagada pelo brilho, com **histerese** para o estado não ficar oscilando.
- **ROI de brilho** opcional: mede só uma região da imagem, como o teto, para não ser enganado pela luz do sol que entra pela janela.
- Alertas com **foto do momento** (`data/alertas/`) e **histórico em CSV** (`data/eventos.csv`).
- **Estimativa de energia (kWh) e custo (R$)** desperdiçados, usando a potência das lâmpadas e a tarifa.
- Resumo ao final do monitoramento e opção de gravar o vídeo anotado.
- Script de **calibração** para descobrir o limiar de brilho de cada sala.

## 3. Tecnologias e modelos

| Tecnologia | Uso |
|---|---|
| **Python 3.10+** | Linguagem do projeto |
| **OpenCV** | Captura de vídeo, conversão para HSV, cálculo de brilho e desenho na tela |
| **Ultralytics YOLOv8** (`yolov8n.pt`) | Detecção de pessoas. É um modelo pré-treinado no dataset COCO, do qual usamos só a classe 0 (`person`). Não precisa de treino e é baixado automaticamente na primeira execução |
| **NumPy** | Operações com as imagens |
| **pytest** | Testes automatizados |

**Como o brilho é medido:** o frame é convertido de BGR para HSV e calculamos a média do canal **V (Value)**, que vai de 0 a 255. Se esse valor ficar acima do limiar calibrado, consideramos a luz acesa.

## 4. Estrutura do projeto

```
salas-vazias-luz-acesa/
├── README.md
├── requirements.txt
├── src/
│   ├── main.py          # programa principal (loop de vídeo)
│   ├── detector.py      # detecção de pessoas com YOLO
│   ├── brilho.py        # análise de brilho + histerese
│   ├── estado.py        # máquina de estados da sala
│   ├── alerta.py        # CSV, fotos dos alertas e estimativa de energia
│   ├── visual.py        # desenho das informações no vídeo
│   └── calibrar.py      # calibração do limiar de brilho
├── tools/
│   └── gerar_video_teste.py   # gera vídeo sintético para testar sem câmera
├── tests/               # testes automatizados (pytest)
├── videos_teste/        # vídeos usados nos testes/demonstração
├── data/                # saídas: eventos.csv e fotos dos alertas
└── docs/                # Etapa 1 (identificação do problema)
```

## 5. Instalação

```bash
git clone https://github.com/<usuario>/salas-vazias-luz-acesa.git
cd salas-vazias-luz-acesa

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

> **Dica:** se o computador não tem placa de vídeo NVIDIA, instale antes a versão do PyTorch só para CPU, que é bem menor:
> `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`

## 6. Como executar

> Todos os comandos devem ser rodados a partir da pasta raiz do projeto.

**Webcam (ao vivo):**
```bash
python src/main.py --fonte 0 --sala "Sala 214-B"
```

**Vídeo gravado (salvando o vídeo anotado):**
```bash
python src/main.py --fonte videos_teste/sala.mp4 --sala "Sala 214-B" --salvar-video saida.mp4
```

**Uma imagem:**
```bash
python src/main.py --fonte foto_sala.jpg
```

**Câmera IP (RTSP):**
```bash
python src/main.py --fonte rtsp://usuario:senha@192.168.0.10:554/stream
```

**Testar sem câmera:** este comando gera um vídeo sintético e roda o sistema nele.
```bash
python tools/gerar_video_teste.py --saida videos_teste/demo_sintetico.mp4
python src/main.py --fonte videos_teste/demo_sintetico.mp4 --sala "Sala Teste"
```

Pressione **Q** para encerrar. Ao sair, o programa mostra um resumo como este:

```
================ RESUMO DO MONITORAMENTO ================
Sala ......................: Sala Teste
Tempo monitorado ..........: 00:00:58
Alertas gerados ...........: 2
Tempo vazia com luz acesa .: 00:00:32 (55.2%)
Energia desperdiçada ......: 0.0019 kWh (potência considerada: 216 W)
Custo estimado ............: R$ 0.0015 (tarifa: R$ 0.80/kWh)
==========================================================
```

### Calibração do brilho (recomendado em cada sala)

```bash
python src/calibrar.py --fonte 0
```
Segure a tecla **A** com a luz acesa, segure **P** com a luz apagada e pressione **Q**. O script sugere o `--limiar` e a `--margem` para essa sala.

Também é possível calibrar com dois vídeos curtos, um gravado com a luz acesa e outro com a luz apagada:
```bash
python src/calibrar.py --acesa videos_teste/acesa.mp4 --apagada videos_teste/apagada.mp4
```

### Parâmetros principais

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `--fonte` | `0` | Webcam (0, 1...), caminho de vídeo/imagem ou URL RTSP |
| `--sala` | `Sala 01` | Nome da sala |
| `--limiar` | `100` | Brilho (0–255) a partir do qual a luz é considerada acesa |
| `--margem` | `5` | Histerese do limiar |
| `--roi` | toda a imagem | Região para medir o brilho: `x,y,largura,altura` |
| `--tolerancia` | `10` | Segundos com a sala vazia e acesa antes de gerar o alerta |
| `--confianca` | `0.4` | Confiança mínima da detecção de pessoas |
| `--intervalo` | `1` | Roda o YOLO a cada N frames (aumenta o FPS em PCs fracos) |
| `--potencia` | `216` | Potência total da iluminação da sala, em W |
| `--tarifa` | `0.80` | Tarifa de energia em R$/kWh |
| `--salvar-video` | — | Grava o vídeo com as anotações |
| `--sem-janela` | — | Roda sem abrir janela (servidor) |

## 7. Saídas

- **`data/eventos.csv`**: histórico de alertas (início e fim, motivo, tempo vazia e acesa, kWh e R$).
- **`data/alertas/*.jpg`**: foto anotada do momento de cada alerta.
- **Vídeo anotado**: gerado quando se usa `--salvar-video`.

## 8. Testes

```bash
python -m pytest -q
```
Os testes cobrem a medição de brilho, a histerese e todas as transições da máquina de estados, incluindo o caso de a pessoa "sumir" por alguns frames sem gerar alarme falso.

## 9. Limitações e melhorias futuras

- **Luz natural:** de dia, a luz que entra pela janela pode deixar a sala clara mesmo com as lâmpadas apagadas. A ROI no teto e a calibração por sala diminuem o problema, mas não eliminam.
- **Ângulo da câmera:** uma pessoa fora do campo de visão ou totalmente escondida não é detectada. A tolerância reduz alarmes falsos nesses casos.
- **Privacidade:** o sistema não grava nem identifica pessoas (só conta se há alguém), e a foto é salva apenas no momento do alerta, quando a sala está vazia. Uma instalação real precisaria de aviso e aprovação da instituição.
- **Melhorias:**
  - Painel web com o status de todas as salas.
  - Notificação para a zeladoria (Telegram ou WhatsApp).
  - Integração com a grade de horários das aulas.
  - Desligamento automático via relé (ESP32).
  - Detecção também do ar-condicionado ligado.
