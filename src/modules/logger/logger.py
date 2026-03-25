from typing import Any, Optional
from .abc.abstractLogger import AbstractLogger
from .consoleLogger import ConsoleLogger
from .fileLogger import FileLogger

class Logger(AbstractLogger):
    def __init__(self, file: Optional[str] = None):
        self.fileHandler = FileLogger(file) if file else None 
        self.consoleHandler = ConsoleLogger()
    
    def info(self, *content: Any):
        if self.fileHandler:
            self.fileHandler.info(*content)

        return self.consoleHandler.info(*content)
    
    def log(self, *content: Any):
        if self.fileHandler:
            self.fileHandler.log(*content)

        return self.consoleHandler.log(*content)

    def warn(self, *content: Any):
        if self.fileHandler:
            self.fileHandler.warn(*content)

        return self.consoleHandler.warn(*content)

    def error(self, *content: Any):
        if self.fileHandler:
            self.fileHandler.error(*content)

        return self.consoleHandler.error(*content)

    def crit(self, *content: Any):
        if self.fileHandler:
            self.fileHandler.crit(*content)

        return self.consoleHandler.crit(*content)

    def debug(self, *content: Any):
        if self.fileHandler:
            self.fileHandler.debug(*content)

        return self.consoleHandler.debug(*content)

    def get(self, *content: Any):
        if self.fileHandler:
            self.fileHandler.get(*content)

        return self.consoleHandler.get(*content)  # Couleur 30

    def post(self, *content: Any):
        if self.fileHandler:
            self.fileHandler.post(*content)

        return self.consoleHandler.post(*content)  # Couleur 202

    def delete(self, *content: Any):
        if self.fileHandler:
            self.fileHandler.delete(*content)

        return self.consoleHandler.delete(*content)