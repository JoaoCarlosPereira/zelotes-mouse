"""Acesso HID ao C-18 via hidapi (Linux, Windows e macOS)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import hid

from zelotes_mouse.protocol import (
    BLOCK_LEN,
    CONTROL_INTERFACE,
    FEATURE_LEN,
    OUTPUT_LEN,
    PID,
    USAGE,
    USAGE_PAGE,
    VID,
    ProtocolError,
    split_block,
    upload_header,
)

RULE_FILE = (
    Path(__file__).resolve().parents[2] / "udev" / "60-zelotes-c18.rules"
)


class MouseError(Exception):
    """Falha ao falar com o mouse."""


class MouseNotFound(MouseError):
    """Nenhuma interface de controle do C-18 apareceu."""


class MousePermissionError(MouseError):
    """O dispositivo existe, mas o usuário não pode abri-lo."""


@dataclass(frozen=True)
class Endpoint:
    path: bytes
    interface_number: int
    usage_page: int
    usage: int
    vendor_id: int
    product_id: int
    manufacturer: str
    product: str

    @property
    def is_control(self) -> bool:
        if self.vendor_id != VID or self.product_id != PID:
            return False
        if self.usage_page == USAGE_PAGE and self.usage == USAGE:
            return True
        # No Linux o backend libusb da hidapi devolve usage 0.
        # Nesse mouse a coleção FF00:FF00 é a interface USB 2.
        return (
            self.usage_page == 0
            and self.usage == 0
            and self.interface_number == CONTROL_INTERFACE
        )

    def label(self) -> str:
        path = self.path.decode("utf-8", "replace")
        name = " ".join(part for part in (self.manufacturer, self.product) if part)
        usage = f"{self.usage_page:04x}:{self.usage:04x}"
        mark = "controle" if self.is_control else "outra"
        title = name or "Zelotes C-18"
        return f"{title}  if={self.interface_number}  usage={usage}  {mark}  {path}"


def list_endpoints() -> list[Endpoint]:
    found: list[Endpoint] = []
    for info in hid.enumerate(VID, PID):
        path = info.get("path") or b""
        if isinstance(path, str):
            path = path.encode()
        interface = info.get("interface_number")
        found.append(
            Endpoint(
                path=path,
                interface_number=-1 if interface is None else int(interface),
                usage_page=int(info.get("usage_page") or 0),
                usage=int(info.get("usage") or 0),
                vendor_id=int(info.get("vendor_id") or 0),
                product_id=int(info.get("product_id") or 0),
                manufacturer=str(info.get("manufacturer_string") or ""),
                product=str(info.get("product_string") or ""),
            )
        )
    return found


def control_endpoints() -> list[Endpoint]:
    return [item for item in list_endpoints() if item.is_control]


class Mouse:
    """Sessão com a interface de controle. Não abre a interface do cursor."""

    def __init__(self, endpoint: Endpoint | None = None) -> None:
        if endpoint is None:
            matches = control_endpoints()
            if not matches:
                raise MouseNotFound(
                    "não achei a interface de controle do Zelotes C-18 (12c9:2003, interface 2)"
                )
            endpoint = matches[0]
        if not endpoint.is_control:
            raise MouseError("esse endpoint não é a interface de controle")
        self.endpoint = endpoint
        self._device = hid.device()
        try:
            self._device.open_path(endpoint.path)
        except OSError as exc:
            raise _open_error(exc) from exc

    def close(self) -> None:
        self._device.close()

    def __enter__(self) -> Mouse:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def send_feature(self, payload: bytes) -> None:
        if len(payload) != FEATURE_LEN:
            raise ProtocolError(f"feature tem {FEATURE_LEN} bytes, recebi {len(payload)}")
        _check_write(self._device.send_feature_report(bytes([0]) + payload), FEATURE_LEN + 1)

    def send_output(self, payload: bytes) -> None:
        if len(payload) != OUTPUT_LEN:
            raise ProtocolError(f"report de saída tem {OUTPUT_LEN} bytes, recebi {len(payload)}")
        _check_write(self._device.write(bytes([0]) + payload), OUTPUT_LEN + 1)

    def upload(self, opcode: int, index: int, block: bytes) -> None:
        """Envia o feature de anúncio e os dois reports de 64 bytes."""
        if len(block) > BLOCK_LEN:
            raise ProtocolError(f"bloco tem no máximo {BLOCK_LEN} bytes")
        self.send_feature(upload_header(opcode, index))
        first, second = split_block(block)
        self.send_output(first)
        time.sleep(0.01)
        self.send_output(second)


def _check_write(written: int, expected: int) -> None:
    if written < 0:
        raise MouseError(f"o HID recusou a escrita ({written})")
    if written not in (expected, expected - 1):
        # Alguns backends contam o report ID, outros só a carga.
        raise MouseError(f"escrita HID incompleta: {written} bytes, esperava {expected}")


def _open_error(exc: OSError) -> MouseError:
    text = str(exc).lower()
    # A hidapi no Linux devolve "open failed" quando o nó USB não é gravável.
    denied = (
        exc.errno in (1, 13)
        or "access" in text
        or "permission" in text
        or "denied" in text
        or "open failed" in text
    )
    if denied:
        return MousePermissionError(
            "sem permissão para abrir a interface de controle.\n"
            f"Copie {RULE_FILE}\n"
            "para /etc/udev/rules.d/ e reconecte o mouse."
        )
    return MouseError(f"não consegui abrir o mouse: {exc}")
