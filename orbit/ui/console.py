from rich.console import Console

from orbit.ui.themes import ORBIT_THEME

console = Console(theme=ORBIT_THEME)
err_console = Console(theme=ORBIT_THEME, stderr=True)
