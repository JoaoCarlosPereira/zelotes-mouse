"""Pacotes HID do Zelotes C-18.

O Windows manda comandos curtos num feature de 8 bytes. O oitavo byte fecha
a soma dos oito em 0xFF. Blocos grandes (cor, DPI, macro) saem depois de um
feature que anuncia 0x80 bytes, em dois reports de saída de 64.
"""

from __future__ import annotations

FEATURE_LEN = 8
OUTPUT_LEN = 64
BLOCK_LEN = 128

VID = 0x12C9
PID = 0x2003
USAGE_PAGE = 0xFF00
USAGE = 0xFF00
CONTROL_INTERFACE = 2

OP_INIT = 0x01
OP_PROFILE = 0x02
OP_POLLING = 0x03
OP_INDEXED = 0x04
OP_LIGHT = 0x0C
OP_UPLOAD_SHARED = 0x0D
OP_UPLOAD_SLOT = 0x0F

# Nomes na ordem em que o Monitor.exe codifica o modo em +0x3AC.
# O texto de fábrica lista Standard, Cycle breathing, Neon, Wave e Flowing.
LIGHT_MODES = (
    ("desligado", "Desligado"),
    ("padrao", "Padrão"),
    ("respiracao", "Respiração"),
    ("neon", "Neon"),
    ("onda", "Onda"),
    ("fluxo", "Fluxo"),
    ("espectro", "Modo 5"),
)

# Ações que o lan.dll mostra e que ainda não têm o pacote 0x0D mapeado.
FACTORY_ACTIONS = (
    "Clique",
    "Menu",
    "Clique do scroll",
    "Clique duplo",
    "Atalho",
    "Botão desligado",
    "DPI: trocar, ciclo, subir, descer",
    "Macro",
    "Troca de perfil",
    "Botão de disparo",
    "Multimídia e teclas do Windows",
    "Ajuste de ponteiro",
    "LED ligado ou desligado pelo botão",
)

# Códigos gravados pelo Monitor.exe no comando 0x03.
# 8, 4, 2 e 1 coincidem com o intervalo em milissegundos de 125–1000 Hz.
# O binário não nomeia a unidade; o mapa é a leitura mais coerente desses quatro valores.
POLLING_CODE_BY_HZ = {
    125: 8,
    250: 4,
    500: 2,
    1000: 1,
}


class ProtocolError(ValueError):
    """Pacote ou argumento fora do que o firmware aceita."""


def checksum(head: bytes) -> int:
    """Byte que faz a soma dos 8 bytes do feature dar 0xFF."""
    if len(head) != 7:
        raise ProtocolError(f"o cabeçalho do feature tem 7 bytes, recebi {len(head)}")
    return (0xFF - (sum(head) & 0xFF)) & 0xFF


def feature(*body: int) -> bytes:
    """Monta um feature de 8 bytes. `body` ocupa o início; o resto fica zero."""
    if len(body) > 7:
        raise ProtocolError("um feature carrega no máximo 7 bytes antes do checksum")
    for value in body:
        if not 0 <= value <= 0xFF:
            raise ProtocolError(f"byte fora de 0..255: {value}")
    head = bytes(body).ljust(7, b"\x00")
    packet = head + bytes([checksum(head)])
    if sum(packet) & 0xFF != 0xFF:
        raise ProtocolError("checksum interno inconsistente")
    return packet


def init_link() -> bytes:
    """Comando fixo 01 88 que o monitor envia na abertura."""
    return feature(OP_INIT, 0x88)


def select_profile(profile: int) -> bytes:
    """Seleciona o perfil. `profile` é base 0, como em Config.ini."""
    _profile(profile)
    return feature(OP_PROFILE, profile + 1)


def settings_packets(profile: int, hz: int) -> list[bytes]:
    """Sequência curta que o monitor manda antes do bloco grande de luz."""
    return [init_link(), select_profile(profile), set_polling(profile, hz)]


def set_polling(profile: int, hz: int) -> bytes:
    """Grava o código de polling do perfil."""
    _profile(profile)
    try:
        code = POLLING_CODE_BY_HZ[hz]
    except KeyError:
        options = ", ".join(str(item) for item in POLLING_CODE_BY_HZ)
        raise ProtocolError(f"polling deve ser um destes Hz: {options}") from None
    return feature(OP_POLLING, profile + 1, code)


def set_indexed(profile: int, value: int) -> bytes:
    """Comando 0x04. O monitor soma 1 ao valor guardado em +0x3A4 do perfil.

    O nome da opção (DPI, modo de cor ou outro) ainda não foi amarrado.
    """
    _profile(profile)
    _byte_index(value, "valor")
    return feature(OP_INDEXED, profile + 1, value + 1)


def upload_header(opcode: int, index: int) -> bytes:
    """Feature que avisa o mouse para receber 128 bytes em seguida."""
    if opcode not in (OP_LIGHT, OP_UPLOAD_SHARED, OP_UPLOAD_SLOT):
        raise ProtocolError(f"opcode de upload desconhecido: {opcode:#x}")
    _byte_index(index, "índice")
    return feature(opcode, index + 1, 0x80)


def split_block(block: bytes) -> tuple[bytes, bytes]:
    """Parte um bloco de até 128 bytes em dois reports de saída."""
    if len(block) > BLOCK_LEN:
        raise ProtocolError(f"bloco tem no máximo {BLOCK_LEN} bytes, recebi {len(block)}")
    padded = block.ljust(BLOCK_LEN, b"\x00")
    return padded[:OUTPUT_LEN], padded[OUTPUT_LEN:]


def _profile(profile: int) -> None:
    if not isinstance(profile, int) or isinstance(profile, bool) or not 0 <= profile <= 7:
        raise ProtocolError("perfil vai de 0 a 7")


def _byte_index(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 254:
        raise ProtocolError(f"{name} vai de 0 a 254")


def encode_dpi_stage(value: int) -> int:
    """Converte o estágio 0–100 no byte que FUN_004077e0 grava no bloco."""
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
        raise ProtocolError("estágio de DPI vai de 0 a 100")
    if value in _DPI_STAGE:
        return _DPI_STAGE[value]
    if value < 51:
        return 4
    return _DPI_PAIRS[(value - 51) // 2]


def light_block(
    mode: str,
    level: int,
    brightness: int,
    speed: int,
    color: tuple[int, int, int],
    dpi: tuple[int, int, int, int, int],
) -> bytes:
    """Bloco de 128 bytes que FUN_00406ab0 envia depois do feature 0x0C.

    Os bytes fixos são os que o monitor escreve na pilha antes de sobrepor
    modo, intensidade, velocidade, cinco estágios de DPI e oito cores.
    """
    mode_id = _mode_id(mode)
    _knob(level, "nível")
    _knob(brightness, "brilho")
    _knob(speed, "velocidade")
    if len(dpi) != 5:
        raise ProtocolError("o mouse guarda cinco estágios de DPI")
    red, green, blue = (_channel(item) for item in color)

    block = bytearray(BLOCK_LEN)
    block[0:2] = b"\xff\xff"
    for offset, value in _LIGHT_TEMPLATE.items():
        block[offset] = value
    mode_byte, param, kind = _mode_wire(mode_id, level)
    block[0x47] = mode_byte
    block[0x48] = param
    block[0x49] = kind
    block[0x4A] = brightness * 10
    block[0x4B] = speed * 10
    stages = [encode_dpi_stage(item) for item in dpi]
    block[0x54:0x59] = bytes(stages)
    block[0x5C:0x61] = bytes(stages)
    block[0x64] = 0x1F
    if mode_id == 1:
        red, green, blue = (_scale_channel(red, level), _scale_channel(green, level), _scale_channel(blue, level))
    for slot in range(8):
        start = 0x68 + slot * 3
        block[start : start + 3] = bytes((red, green, blue))
    return bytes(block)


def _mode_id(mode: str) -> int:
    for index, (key, _label) in enumerate(LIGHT_MODES):
        if mode == key:
            return index
    names = ", ".join(key for key, _label in LIGHT_MODES)
    raise ProtocolError(f"modo de luz desconhecido. Use um destes: {names}")


def _mode_wire(mode_id: int, level: int) -> tuple[int, int, int]:
    """Bytes 0x47, 0x48 e 0x49, no mesmo formato do monitor."""
    if mode_id == 0:
        return 0, 0, 0
    if mode_id == 1:
        if level not in (1, 2, 3):
            raise ProtocolError("no modo padrão o nível é 1, 2 ou 3")
        return 1, level, 3
    if mode_id == 2:
        return 2, (level << 2) & 0xFF, 10
    if mode_id == 3:
        return 3, (level << 2) & 0xFF, 0
    if mode_id == 4:
        return 4, (level * 3) & 0xFF, 0x10
    if mode_id == 5:
        if level == 1:
            param = 0x3C
        elif level == 2:
            param = 0x5F
        else:
            param = 0x78
        return 6, param, 10
    return 5, (level << 2) & 0xFF, 10


def _scale_channel(channel: int, level: int) -> int:
    """O modo padrão reduz o canal como o monitor faz com a paleta."""
    if level == 1:
        return channel
    third = ((channel * 0x55555556) & 0xFFFFFFFFFFFFFFFF) >> 32
    if level == 2:
        return (third * 2) & 0xFF
    return third & 0xFF


def _knob(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 10:
        raise ProtocolError(f"{name} vai de 0 a 10")


def _channel(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 255:
        raise ProtocolError("cada canal de cor vai de 0 a 255")
    return value


# Bytes que FUN_00406ab0 coloca na pilha e que o restante do bloco não cobre.
_LIGHT_TEMPLATE = {
    0x40: 0x0F,
    0x42: 0x1E,
    0x43: 10,
    0x44: 0x19,
    0x45: 0x19,
    0x46: 5,
    0x4C: 1,
    0x4D: 0xC0,
    0x4E: 0xF0,
    0x4F: 3,
    0x50: 1,
    0x51: 1,
    0x52: 0x19,
    0x53: 0x19,
    0x59: 0x5C,
    0x5A: 0x73,
    0x61: 0x5C,
    0x62: 0x73,
    0x65: 0xFF,
}

_DPI_STAGE = {
    3: 0x06,
    4: 0x08,
    5: 0x0B,
    6: 0x0D,
    7: 0x0F,
    8: 0x12,
    9: 0x14,
    10: 0x16,
    11: 0x19,
    12: 0x1B,
    13: 0x1D,
    14: 0x20,
    15: 0x22,
    16: 0x24,
    17: 0x27,
    18: 0x29,
    19: 0x2B,
    20: 0x2E,
    21: 0x30,
    22: 0x32,
    23: 0x34,
    24: 0x37,
    25: 0x39,
    26: 0x3B,
    27: 0x3E,
    28: 0x40,
    29: 0x42,
    30: 0x45,
    31: 0x47,
    32: 0x49,
    33: 0x4C,
    34: 0x4E,
    35: 0x50,
    36: 0x53,
    37: 0x55,
    38: 0x57,
    39: 0x5A,
    40: 0x5C,
    41: 0x5E,
    42: 0x61,
    43: 0x63,
    44: 0x65,
    45: 0x68,
    46: 0x6A,
    47: 0x6C,
    48: 0x6F,
    49: 0x71,
    50: 0x73,
}

_DPI_PAIRS = (
    0xBB, 0xBE, 0xC0, 0xC2, 0xC5, 0xC7, 0xC9, 0xCC, 0xCE, 0xD0,
    0xD3, 0xD5, 0xD7, 0xDA, 0xDC, 0xDE, 0xE1, 0xE3, 0xE5, 0xE8,
    0xEA, 0xEC, 0xEF, 0xF1, 0xF3,
)
