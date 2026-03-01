from rich.theme import Theme

# Orbit color palette
ORBIT_BLUE = "#4A9EFF"
SUCCESS_GREEN = "#00CC66"
WARNING_YELLOW = "#FFB800"
ERROR_RED = "#FF4444"

ORBIT_THEME = Theme(
    {
        "orbit.blue": ORBIT_BLUE,
        "orbit.success": SUCCESS_GREEN,
        "orbit.warning": WARNING_YELLOW,
        "orbit.error": ERROR_RED,
        "orbit.info": ORBIT_BLUE,
        "orbit.step": "bold " + ORBIT_BLUE,
        "orbit.command": "bold cyan",
        "orbit.risk.safe": SUCCESS_GREEN,
        "orbit.risk.caution": WARNING_YELLOW,
        "orbit.risk.destructive": ERROR_RED,
        "orbit.risk.nuclear": "bold red on white",
    }
)
