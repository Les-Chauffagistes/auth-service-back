import abc
from datetime import datetime
from typing import Any

class AbstractLogger(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def info(self, *content: Any) -> Any:
        pass
    
    @abc.abstractmethod
    def warn(self, *content: Any) -> Any:
        pass

    @abc.abstractmethod
    def error(self, *content: Any) -> Any:
        pass

    @abc.abstractmethod
    def crit(self, *content: Any) -> Any:
        pass

    @abc.abstractmethod
    def debug(self, *content: Any) -> Any:
        pass

    @abc.abstractmethod
    def get(self, *content: Any) -> Any:
        pass

    @abc.abstractmethod
    def post(self, *content: Any) -> Any:
        pass

    @abc.abstractmethod
    def delete(self, *content: Any) -> Any:
        pass

    def _formatter(self, datetime_obj: datetime) -> str:
        date_str = datetime_obj.strftime('%d/%m/%Y')
        hour_str = datetime_obj.strftime('%H:%M:%S')
        return f'{date_str} à {hour_str} '