"""
LuminaTerm Chat - Simple Terminal AI Chatbot

Required dependencies (install with pip):
- requests
- pyfiglet
- colorama
Windows:
    pip install requests pyfiglet colorama
Mac/Linux:
    pip3 install requests pyfiglet colorama

"""

import json
import sys
import requests
from typing import List, Dict

from pyfiglet import Figlet
from colorama import init as colorama_init, Fore, Style

# ---------------- Configuration ----------------

# Keep the placeholder exactly as required. Insert your key in place of <OPENROUTER_API_KEY>.
OPENROUTER_API_KEY = "Bearer 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"

OPENROUTER_TITLE = "LuminaTerm Chat"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "deepseek/deepseek-r1-0528:free"

# Chatbot branding
CHATBOT_NAME = "LuminaTerm"
EXIT_COMMANDS = {"/exit", "exit", "/quit", "quit", ":q"}


# ---------------- Simple Markdown Renderer ----------------

def render_markdown_to_terminal(text: str) -> str:
    """
    Very small, custom Markdown-to-terminal renderer.

    Supported:
    - Headings: #, ##, ### at line start
    - Bold: **text**
    - Italic: *text*
    - Bullet lists: lines starting with "-" or "*"
    - Inline code: `code`
    Returns a string with ANSI color/style codes suitable for printing.
    """

    def style_heading(line: str) -> str:
        stripped = line.lstrip()
        if stripped.startswith("### "):
            content = stripped[4:]
            return f"{Style.BRIGHT}{Fore.MAGENTA}### {content}{Style.RESET_ALL}"
        elif stripped.startswith("## "):
            content = stripped[3:]
            return f"{Style.BRIGHT}{Fore.CYAN}## {content}{Style.RESET_ALL}"
        elif stripped.startswith("# "):
            content = stripped[2:]
            return f"{Style.BRIGHT}{Fore.GREEN}# {content}{Style.RESET_ALL}"
        return line

    def style_bullets(line: str) -> str:
        stripped = line.lstrip()
        if stripped.startswith("- "):
            content = stripped[2:]
            return f"  {Fore.YELLOW}- {Style.RESET_ALL}{content}"
        if stripped.startswith("* "):
            content = stripped[2:]
            return f"  {Fore.YELLOW}* {Style.RESET_ALL}{content}"
        return line

    def replace_inline_code(s: str) -> str:
        # Simple inline code highlighting: `code`
        result = ""
        in_code = False
        i = 0
        while i < len(s):
            if s[i] == "`":
                if not in_code:
                    result += f"{Fore.CYAN}{Style.DIM}"
                    in_code = True
                else:
                    result += f"{Style.RESET_ALL}"
                    in_code = False
                i += 1
            else:
                result += s[i]
                i += 1
        if in_code:
            # Close style if unbalanced backtick
            result += Style.RESET_ALL
        return result

    def replace_bold_and_italic(s: str) -> str:
        # Bold: **text** => bright
        # Italic: *text*  => dim
        result = ""
        i = 0
        bold = False
        italic = False
        while i < len(s):
            if s.startswith("**", i):
                if not bold:
                    result += Style.BRIGHT
                    bold = True
                else:
                    result += Style.RESET_ALL
                    bold = False
                i += 2
            elif s[i] == "*" and not s.startswith("**", i):
                if not italic:
                    result += Style.DIM
                    italic = True
                else:
                    result += Style.RESET_ALL
                    italic = False
                i += 1
            else:
                result += s[i]
                i += 1
        if bold or italic:
            result += Style.RESET_ALL
        return result

    lines = text.splitlines()
    rendered_lines = []
    for line in lines:
        line = style_heading(line)
        line = style_bullets(line)
        line = replace_inline_code(line)
        line = replace_bold_and_italic(line)
        rendered_lines.append(line)

    return "\n".join(rendered_lines)


# ---------------- OpenRouter API ----------------
def call_openrouter(messages: List[Dict[str, str]]) -> str:
    """
    Call the OpenRouter chat completions API with the given message history.
    Returns the assistant's reply text, or raises an exception on error.
    """
    headers = {
        "Authorization": OPENROUTER_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
    }

    try:
        response = requests.post(
            url=OPENROUTER_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=60,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Network error: {e}") from e

    if response.status_code != 200:
        raise RuntimeError(
            f"API error: HTTP {response.status_code} - {response.text[:500]}"
        )

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        raise RuntimeError("Failed to parse API response as JSON") from e

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError("Unexpected API response format") from e


# ---------------- UI helpers ----------------

def print_banner() -> None:
    """Print the startup banner using pyfiglet and colorama."""
    fig = Figlet(font="Slant")
    title = fig.renderText(CHATBOT_NAME)
    print(f"{Fore.CYAN}{Style.BRIGHT}{title}{Style.RESET_ALL}")
    print(
        f"{Fore.GREEN}Welcome to {CHATBOT_NAME} - a minimal OpenRouter terminal chat client."
        f"{Style.RESET_ALL}"
    )
    print(
        f"{Fore.YELLOW}Type your message and press Enter. "
        f"Type {Fore.RED}/exit{Fore.YELLOW} or {Fore.RED}/quit{Fore.YELLOW} to leave."
        f"{Style.RESET_ALL}\n"
    )


def print_system(msg: str) -> None:
    print(f"{Fore.MAGENTA}{Style.BRIGHT}[system]{Style.RESET_ALL} {msg}")


def print_user_prompt() -> None:
    sys.stdout.write(f"{Fore.BLUE}{Style.BRIGHT}[you]{Style.RESET_ALL} ")
    sys.stdout.flush()


def print_assistant(msg: str) -> None:
    print(f"{Fore.CYAN}{Style.BRIGHT}[{CHATBOT_NAME}]{Style.RESET_ALL}")
    rendered = render_markdown_to_terminal(msg)
    print(rendered)
    print()  # blank line


def print_error(msg: str) -> None:
    print(f"{Fore.RED}{Style.BRIGHT}[error]{Style.RESET_ALL} {msg}")


# ---------------- Main loop ----------------

def main() -> None:
    colorama_init(autoreset=True)

    print_banner()

    messages: List[Dict[str, str]] = []

    while True:
        print_user_prompt()
        try:
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print_system("Exiting. Goodbye.")
            break

        if not user_input:
            print_error("Empty message. Please type something or /exit to quit.")
            continue

        if user_input.lower() in EXIT_COMMANDS:
            print_system("Goodbye.")
            break

        messages.append({"role": "user", "content": user_input})

        print_system("Thinking...")

        try:
            assistant_reply = call_openrouter(messages)
        except RuntimeError as e:
            print_error(str(e))
            # Allow user to continue chatting or exit
            continue

        messages.append({"role": "assistant", "content": assistant_reply})
        print_assistant(assistant_reply)


if __name__ == "__main__":
    main()
