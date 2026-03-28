from importlib import import_module

from .bech32_fallback import bech32_decode as fallback_bech32_decode
from .bech32_fallback import bech32_encode as fallback_bech32_encode


def _load_pypi_bech32():
    try:
        module = import_module("bech32")
    except ModuleNotFoundError:
        return None

    required_symbols = ("bech32_encode", "bech32_decode", "convertbits")
    if not all(hasattr(module, symbol) for symbol in required_symbols):
        return None

    return module


def encode_lnurl(url: str) -> str:
    bech32_module = _load_pypi_bech32()
    if bech32_module is not None:
        words = bech32_module.convertbits(url.encode("utf-8"), 8, 5)
        if words is None:
            raise ValueError("pypi bech32 failed to convert url to words")
        return bech32_module.bech32_encode("lnurl", words)

    return fallback_bech32_encode("lnurl", url.encode("utf-8"))


def decode_lnurl(lnurl: str) -> str:
    bech32_module = _load_pypi_bech32()
    if bech32_module is not None:
        hrp, words = bech32_module.bech32_decode(lnurl)
        if hrp != "lnurl" or words is None:
            raise ValueError("invalid lnurl bech32 payload")
        data = bech32_module.convertbits(words, 5, 8, False)
        if data is None:
            raise ValueError("pypi bech32 failed to decode words")
        return bytes(data).decode("utf-8")

    return fallback_bech32_decode(lnurl).decode("utf-8")
