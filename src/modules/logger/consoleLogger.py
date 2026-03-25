import inspect, re, shutil, traceback
from datetime import datetime
from typing import Any, Optional
from .abc.abstractLogger import AbstractLogger
from .line import Line

class ConsoleLogger(AbstractLogger):
    def __init__(self, file: Optional[str] = None):
        """Écrit les logs dans la console et/ou dans un fichier si spécifié."""
        self.file = file
        self.curent_line = 0
        self.lines: list[str] = []
        self._line_data: list[tuple[str, int]] = []
    
    @staticmethod
    def strip_ansi(s):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', s)

    def count_lines(self, text: str) -> int:
        """Compte le nombre de lignes affichées dans la console, y compris les retours à la ligne forcés."""
        text = self.strip_ansi(text)  # Supprimer les codes ANSI pour le calcul
        terminal_width = shutil.get_terminal_size((80, 20)).columns  # Valeur par défaut si non détecté
        lines = 0
        for line in text.strip().split("\n"):  # Prendre en compte les retours à la ligne explicites
            lines += (len(line) // terminal_width) + 1  # Division entière pour compter les lignes réelles
        return lines

    def log(self, level: str, color_code: str, *content: Any):
        frame = inspect.stack()
        f2 = frame[3]
        caller = f2.function if f2.function != '<module>' else 'Main thread'
        filename = f2.filename.split('/')[-1]  # Just the file name, not the full path
        lineno = f2.lineno
        message = ' '.join(map(str, content)).strip()
        timestamp = self._formatter(datetime.now())

        if level not in ['GET', 'POST', 'DELETE']:
            caller_info = f"{filename}:{lineno} {caller}"
            caller_info = f"\33[0;96m {caller_info}\33[0;96m"
        
        else:
            caller_info = ''
    
        text = f"\33[90m{timestamp}\033[1;{color_code};40m[{level}]{caller_info}\033[0;0m {message}"
        self.lines.append(text)
        self.curent_line += self.count_lines(text)
        line_count = self.count_lines(text)
        self._line_data.append((text, line_count))
        print(text)
        index = len(self._line_data) -1  # index réel

        return Line(timestamp, color_code, level, caller_info, content, index, self)
        
    def info(self, *content: Any):
        return self.log('INFO', '32', *content)

    def warn(self, *content: Any):
        return self.log('WARN', '33', *content)

    def error(self, *content: Any):
        return self.log('ERROR', '38;5;166', *content, traceback.format_exc())

    def crit(self, *content: Any):
        return self.log('CRIT', '38;5;196', *content)

    def debug(self, *content: Any):
        return self.log('DEBUG', '38;5;63', *content)

    def get(self, *content: Any):
        return self.log('GET', '38;5;36', *content)  # Couleur 30

    def post(self, *content: Any):
        return self.log('POST', '38;5;172', *content)  # Couleur 202

    def delete(self, *content: Any):
        return self.log('DELETE', '38;5;160', *content)  # Couleur 160

    def test(self):
        for i in range(255):
            self.log('ERROR', f'38;5;{i}', f"test {i}")