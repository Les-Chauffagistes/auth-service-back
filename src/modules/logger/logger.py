import sys
from typing import Any, Optional

from loguru import logger as _logger

# Niveaux additionnels utilisés par le middleware HTTP (voir src/middlewares/logger.py).
# On enregistre nos propres noms ("WARN"/"CRIT" plutôt que "WARNING"/"CRITICAL") pour
# conserver le rendu court d'origine ([INFO][WARN][ERROR][CRIT][DEBUG][GET][POST][DELETE]).
_logger.remove()
for _name, _no, _color in (
    ("WARN", 30, "<bold><yellow>"),
    ("CRIT", 50, "<bold><fg 196>"),
    ("GET", 21, "<bold><fg 36>"),
    ("POST", 22, "<bold><fg 172>"),
    ("DELETE", 23, "<bold><fg 160>"),
):
    _logger.level(_name, no=_no, color=_color)

_logger.level("INFO", color="<bold><green>")
_logger.level("ERROR", color="<bold><fg 166>")
_logger.level("DEBUG", color="<bold><fg 63>")

_REQUEST_LEVELS = ("GET", "POST", "DELETE")
_TIME_FORMAT = "DD/MM/YYYY à HH:mm:ss"


def _console_format(record: dict) -> str:
    if record["level"].name in _REQUEST_LEVELS:
        return f"<fg 8>{{time:{_TIME_FORMAT}}} </fg 8><level>[{{level.name}}]</level> {{message}}\n"
    # {exception} doit être explicite ici : loguru ne l'ajoute automatiquement
    # que pour les formats "chaîne", pas pour les formats "fonction" comme celui-ci.
    return (
        f"<fg 8>{{time:{_TIME_FORMAT}}} </fg 8><level>[{{level.name}}]</level> "
        "<light-cyan>{name}:{line} {function}</light-cyan> {message}\n{exception}"
    )


_FILE_FORMAT = f"{{time:{_TIME_FORMAT}}}[{{level.name}}] {{name}}:{{line}} {{message}}"

_logger.add(sys.stdout, format=_console_format, colorize=True, backtrace=False, diagnose=False)


class Logger:
    """Façade compatible avec l'ancien module maison, adossée à loguru."""

    def __init__(self, file: Optional[str] = None):
        if file:
            _logger.add(
                file,
                format=_FILE_FORMAT,
                rotation="10 MB",
                retention="14 days",
                backtrace=False,
                diagnose=False,
            )

    @staticmethod
    def _message(content: tuple) -> str:
        return " ".join(map(str, content)).strip()

    def info(self, *content: Any) -> None:
        _logger.opt(depth=1).info(self._message(content))

    def log(self, *content: Any) -> None:
        _logger.opt(depth=1).info(self._message(content))

    def warn(self, *content: Any) -> None:
        _logger.opt(depth=1).log("WARN", self._message(content))

    def error(self, *content: Any) -> None:
        has_active_exception = sys.exc_info()[0] is not None
        _logger.opt(depth=1, exception=has_active_exception).error(self._message(content))

    def crit(self, *content: Any) -> None:
        _logger.opt(depth=1).log("CRIT", self._message(content))

    def debug(self, *content: Any) -> None:
        _logger.opt(depth=1).debug(self._message(content))

    def get(self, *content: Any) -> None:
        _logger.opt(depth=1).log("GET", self._message(content))

    def post(self, *content: Any) -> None:
        _logger.opt(depth=1).log("POST", self._message(content))

    def delete(self, *content: Any) -> None:
        _logger.opt(depth=1).log("DELETE", self._message(content))
