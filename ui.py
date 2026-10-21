import os
if os.name == "nt":
    os.system("")
Color = {
    "cyan": "\033[96m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def style(text, color):
    if os.getenv("NO_COLOR") or not os.isatty(1):
        return str(text)
    return "%s%s%s" % (Color[color], text, Color["reset"])


def banner(title, subtitle=None):
    line = "=" * max(34, len(title) + 8)
    print(style(line, "cyan"))
    print(style("  %s" % title, "bold"))
    if subtitle:
        print(style("  %s" % subtitle, "cyan"))
    print(style(line, "cyan"))


def section(title):
    print("\n%s" % style("-- %s --" % title, "cyan"))


def show_menu(title, options, prompt="Select an option: "):
    section(title)
    for key, label in options:
        print("  %s  %s" % (style(str(key), "bold"), label))
    return input(style(prompt, "bold")).strip()


def success(message):
    print(style("[OK] %s" % message, "green"))


def error(message):
    print(style("[!] %s" % message, "red"))


def info(message):
    print(style(message, "yellow"))
