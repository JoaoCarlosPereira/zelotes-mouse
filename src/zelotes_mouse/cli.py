"""Linha de comando do Zelotes C-18."""

from __future__ import annotations

import argparse
import sys

from zelotes_mouse.device import (
    Mouse,
    MouseError,
    MouseNotFound,
    control_endpoints,
    list_endpoints,
)
from zelotes_mouse.protocol import (
    POLLING_CODE_BY_HZ,
    ProtocolError,
    feature,
    init_link,
    select_profile,
    set_indexed,
    set_polling,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zelotes-mouse",
        description="Controla o mouse Zelotes C-18. Sem comando, abre a janela de desktop.",
    )
    commands = parser.add_subparsers(dest="command")

    app = commands.add_parser("app", help="Abre a janela e a API local")
    app.add_argument("--port", type=int, default=8765)
    api = commands.add_parser("api", help="Sobe só a API local, sem janela")
    api.add_argument("--port", type=int, default=8765)
    gui = commands.add_parser("gui", help="Abre a janela de desktop")
    gui.add_argument("--port", type=int, default=8765)

    commands.add_parser("devices", help="Lista as interfaces HID do mouse")

    commands.add_parser("init", help="Envia o feature fixo 01 88")

    profile = commands.add_parser("profile", help="Seleciona o perfil gravado no mouse")
    profile.add_argument("perfil", type=int, help="Perfil de 1 a 8, como na tela do programa")

    polling = commands.add_parser("polling", help="Grava a taxa de polling do perfil")
    polling.add_argument("perfil", type=int, help="Perfil de 1 a 8")
    polling.add_argument("hz", type=int, choices=sorted(POLLING_CODE_BY_HZ), help="125, 250, 500 ou 1000")

    indexed = commands.add_parser(
        "indexed",
        help="Envia o comando 0x04 (opção por perfil ainda sem nome confirmado)",
    )
    indexed.add_argument("perfil", type=int, help="Perfil de 1 a 8")
    indexed.add_argument("valor", type=int, help="Valor base 0, de 0 a 254")

    raw = commands.add_parser("feature", help="Envia um feature de até 7 bytes em hexadecimal")
    raw.add_argument("bytes", nargs="+", help="Ex.: 01 88")

    args = parser.parse_args(argv)
    try:
        if args.command in (None, "app", "gui"):
            from zelotes_mouse.desktop import run

            return run(port=getattr(args, "port", 8765))
        if args.command == "api":
            from zelotes_mouse.gui import serve

            serve(port=args.port)
            return 0
        if args.command == "devices":
            return _devices()
        if args.command == "init":
            return _send(init_link(), "inicialização")
        if args.command == "profile":
            packet = select_profile(_user_profile(args.perfil))
            return _send(packet, f"perfil {args.perfil}")
        if args.command == "polling":
            packet = set_polling(_user_profile(args.perfil), args.hz)
            return _send(packet, f"polling {args.hz} Hz no perfil {args.perfil}")
        if args.command == "indexed":
            packet = set_indexed(_user_profile(args.perfil), args.valor)
            return _send(packet, f"comando 04 do perfil {args.perfil}")
        if args.command == "feature":
            packet = feature(*_parse_hex(args.bytes))
            return _send(packet, "feature")
    except (ProtocolError, MouseError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    parser.error(f"comando desconhecido: {args.command}")
    return 2


def _devices() -> int:
    endpoints = list_endpoints()
    if not endpoints:
        print("nenhum Zelotes C-18 (12c9:2003) no USB")
        return 1
    for endpoint in endpoints:
        print(endpoint.label())
    chosen = control_endpoints()
    if not chosen:
        print("a interface de controle não apareceu")
        return 1
    print(f"controle: {chosen[0].label()}")
    return 0


def _send(packet: bytes, what: str) -> int:
    print(f"{what}: {packet.hex(' ')}")
    with Mouse() as mouse:
        mouse.send_feature(packet)
    print("enviado")
    return 0


def _user_profile(perfil: int) -> int:
    if not 1 <= perfil <= 8:
        raise ProtocolError("o perfil da linha de comando vai de 1 a 8")
    return perfil - 1


def _parse_hex(parts: list[str]) -> list[int]:
    text = "".join(parts).replace(" ", "").replace(":", "")
    if len(text) % 2:
        raise ProtocolError("hexadecimal incompleto")
    try:
        return list(bytes.fromhex(text))
    except ValueError as exc:
        raise ProtocolError("hexadecimal inválido") from exc


if __name__ == "__main__":
    raise SystemExit(main())
