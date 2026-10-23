# Zelotes C-18

Controle de código aberto para o mouse **Zelotes C-18** no Linux. A janela segue o programa de fábrica: botões, desempenho, iluminação, macros, dois perfis e uma API local para outros sistemas.

By [João Carlos Pereira](https://github.com/JoaoCarlosPereira).

Licença: [Apache 2.0](LICENSE).

## O que o programa grava no mouse

- Perfil ativo (1 ou 2 na janela)
- Taxa de resposta: 125, 250, 500 ou 1000 Hz
- Luz e cor, brilho, velocidade e modo
- Os cinco estágios de DPI, no mesmo bloco da luz

**Aplicar** envia luz e DPI juntos. A primeira gravação substitui os estágios que já estavam no mouse pelos cinco números da tela.

Atribuição de botão e macro ficam salvas neste computador. O programa ainda não envia esses dados ao mouse.

## Requisitos

- Linux com sessão gráfica
- Python 3.12 ou mais novo, se for instalar pelo fonte
- Mouse Zelotes C-18 (`12c9:2003`)
- Permissão de leitura e escrita no HID, pela regra udev incluída

A interface USB 0 é a do cursor. O programa não a abre.

## Instalador

O instalador compilado para Linux x86_64 está na [release v0.1.0](https://github.com/JoaoCarlosPereira/zelotes-mouse/releases/tag/v0.1.0).

```bash
chmod +x zelotes-mouse-0.1.0-linux-x86_64.run
./zelotes-mouse-0.1.0-linux-x86_64.run
```

Ele copia o programa para `~/.local/bin`, coloca o atalho na grade de aplicativos e pede, por uma janela gráfica, para instalar a regra udev. Reconecte o mouse depois disso. No GNOME, use **Adicionar aos favoritos** para fixar na barra.

## Fonte

```bash
uv sync
uv run zelotes-mouse
```

Sem o [uv](https://docs.astral.sh/uv/), qualquer ambiente Python 3.12 com `hidapi` e `PySide6` serve:

```bash
pip install .
zelotes-mouse
```

A regra udev está em `udev/60-zelotes-c18.rules`.

O instalador Linux é gerado com PyInstaller e empacotado por `packaging/linux/install.sh`:

```bash
uv run --with pyinstaller pyinstaller --noconfirm --clean --name zelotes-mouse --onefile \
  --paths src --collect-submodules zelotes_mouse --collect-binaries hid \
  --add-data "src/zelotes_mouse/ui:zelotes_mouse/ui" --hidden-import hid \
  src/zelotes_mouse/__init__.py
```

## API local

Com a janela aberta, a API escuta em `http://127.0.0.1:8765`.

| Método | Caminho | Uso |
| --- | --- | --- |
| GET | `/api/status` | Mouse presente, permitido ou ausente |
| GET | `/api/state` | Perfil, luz, DPI e botões salvos |
| GET | `/api/capabilities` | O que já é enviado ao mouse |
| POST | `/api/state` | Grava o estado só neste computador |
| POST | `/api/apply` | Envia perfil e polling; com `luz` ou `dpi`, grava também o bloco de luz |

`zelotes-mouse api` sobe só a API, sem janela.

## Linha de comando

```bash
zelotes-mouse devices
zelotes-mouse profile 1
zelotes-mouse polling 1 1000
```
