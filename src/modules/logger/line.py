from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .logger import ConsoleLogger

class Line:
    def __init__(self, timestamp: str, color_code: str, level: str, caller_info: str, content: tuple[str], line: int, log: 'ConsoleLogger') -> None:
        self._timestamp = timestamp
        self._color_code = color_code
        self._level = level
        self._caller_info = caller_info
        self._content = content
        self._line = line
        self._log = log
    
    def _move_cursor_up(self, n):
        print(f"\033[{n}A", end='')

    def _move_cursor_down(self, n):
        print(f"\033[{n}B", end='')
    
    def _clear_line(self):
        print("\033[K", end='')
    
    def add_text(self, *content):
        self._content += content
    
    def set_text(self, *content):
       self._content = content

    def _edit(self):
        # Recalcul dynamique du décalage
        offset = sum(line_count for _, line_count in self._log._line_data[self._line:])
        self._move_cursor_up(offset)
        self._clear_line()
        message = ' '.join(map(str, self._content))
        text = f"\33[90m{self._timestamp}\033[1;{self._color_code};40m[{self._level}]{self._caller_info}\033[0;0m {message}"
        print(text)

        # Mise à jour du buffer
        new_line_count = self._log.count_lines(text)
        self._log._line_data[self._line] = (text, new_line_count)
        self._log.curent_line = sum(count for _, count in self._log._line_data)

        self._move_cursor_down(sum(line_count for _, line_count in self._log._line_data[self._line:]))

    def edit_print(self):
        self._edit()
    
    def info(self):
        self._level = 'INFO'
        self._color_code = '32'
        self._edit()

    def warn(self):
        self._level = 'WARN'
        self._color_code = '33'
        self._edit()

    def crit(self):
        self._level = 'CRIT'
        self._color_code = '31'
        self._edit()

    def debug(self):
        self._level = 'DEBUG'
        self._color_code = '95', 
        self._edit()

    def get(self):
        self._level = 'GET'
        self._color_code = '38;5;30'
        self._edit()

    def post(self):
        self._level = 'POST'
        self._color_code = '38;5;202'
        self._edit()