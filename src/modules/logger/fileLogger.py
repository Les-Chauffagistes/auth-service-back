import inspect, traceback
from datetime import datetime
from typing import Any
from .abc.abstractLogger import AbstractLogger

class FileLogger(AbstractLogger):
    def __init__(self, file: str):
        """Écrit les logs dans la console et/ou dans un fichier si spécifié."""
        self.file = file
        self.curent_line = 0
        self.lines: list[str] = []
        self._line_data: list[tuple[str, int]] = []

    def log(self, level: str, *content: Any):
        frame = inspect.stack()[3]
        caller = frame.function if frame.function != '<module>' else 'Main thread'
        filename = frame.filename.split('/')[-1]  # Just the file name, not the full path
        lineno = frame.lineno
        message = ' '.join(map(str, content)).strip()
        timestamp = self._formatter(datetime.now())
        
        caller_info_for_file = f" {filename}:{lineno}"
        try:
            with open(self.file, 'a') as file:
                file.writelines(f"{timestamp}[{level}]{caller_info_for_file} {message}\n")
        
        except: pass
        
    def info(self, *content: Any):
        return self.log('INFO', *content)

    def warn(self, *content: Any):
        return self.log('WARNING', *content)

    def error(self, *content: Any):
        return self.log('ERROR', *content, traceback.format_exc())

    def crit(self, *content: Any):
        return self.log('CRITICAL',  *content)

    def debug(self, *content: Any):
        return self.log('DEBUG', *content)

    def get(self, *content: Any):
        return self.log('GET', *content)  # Couleur 30

    def post(self, *content: Any):
        return self.log('POST', *content)  # Couleur 202

    def delete(self, *content: Any):
        return self.log('DELETE', *content)  # Couleur 160