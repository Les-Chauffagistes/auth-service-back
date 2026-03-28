CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32_polymod(values: list[int]) -> int:
    generator = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for index in range(5):
            if (top >> index) & 1:
                checksum ^= generator[index]
    return checksum


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(char) >> 5 for char in hrp] + [0] + [ord(char) & 31 for char in hrp]


def _bech32_create_checksum(hrp: str, data: list[int]) -> list[int]:
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - index)) & 31 for index in range(6)]


def _convertbits(data: bytes | list[int], frombits: int, tobits: int, pad: bool = True) -> list[int]:
    accumulator = 0
    bits = 0
    result: list[int] = []
    max_value = (1 << tobits) - 1
    max_accumulator = (1 << (frombits + tobits - 1)) - 1

    for value in data:
        if value < 0 or value >> frombits:
            raise ValueError("invalid value for convertbits")
        accumulator = ((accumulator << frombits) | value) & max_accumulator
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            result.append((accumulator >> bits) & max_value)

    if pad:
        if bits:
            result.append((accumulator << (tobits - bits)) & max_value)
    elif bits >= frombits or ((accumulator << (tobits - bits)) & max_value):
        raise ValueError("invalid padding for convertbits")

    return result


def bech32_encode(hrp: str, payload: bytes) -> str:
    data = _convertbits(payload, 8, 5)
    combined = data + _bech32_create_checksum(hrp, data)
    return hrp + "1" + "".join(CHARSET[value] for value in combined)


def bech32_decode(value: str) -> bytes:
    separator = value.rfind("1")
    if separator < 1:
        raise ValueError("invalid bech32 string")

    data_part = value[separator + 1:]
    if len(data_part) < 6:
        raise ValueError("bech32 checksum is missing")

    charset_map = {char: index for index, char in enumerate(CHARSET)}
    data = [charset_map[char] for char in data_part.lower()]
    payload = data[:-6]
    return bytes(_convertbits(payload, 5, 8, pad=False))
