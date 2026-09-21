import os


_COLORS = {
    "cyan": "\033[96m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def _style(text, color):
    if os.getenv("NO_COLOR") or not os.isatty(1):
        return str(text)
    return "%s%s%s" % (_COLORS[color], text, _COLORS["reset"])


def banner(title, subtitle=None):
    line = "=" * max(34, len(title) + 8)
    print(_style(line, "cyan"))
    print(_style("  %s" % title, "bold"))
    if subtitle:
        print(_style("  %s" % subtitle, "cyan"))
    print(_style(line, "cyan"))


def section(title):
    print("\n%s" % _style("-- %s --" % title, "cyan"))


def show_menu(title, options, prompt="Select an option: "):
    section(title)
    for key, label in options:
        print("  %s  %s" % (_style(str(key), "bold"), label))
    return input(_style(prompt, "bold")).strip()


def success(message):
    print(_style("[OK] %s" % message, "green"))


def error(message):
    print(_style("[!] %s" % message, "red"))


def info(message):
    print(_style(message, "yellow"))
