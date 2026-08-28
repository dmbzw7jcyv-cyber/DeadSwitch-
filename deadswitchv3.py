#!/usr/bin/env python3
"""
Deadswitch v3 - self-destructing secret keeper
Part of Templar Studios | GPL v3.0

Features:
  - Hidden code input (getpass)
  - Salted SHA-256 code hashing
  - Time selector (10s to 24h or custom)
  - Full timer reset on correct code
  - Real-time countdown tracking
  - 5 failed attempts destroys secret
  - ASCII art for all states

Works fully in ish, a-shell, linux, macOS.

Usage:
  deadswitchv3.py
"""

import sys
import os
import time
import hashlib
import secrets
import getpass
import platform
from typing import Tuple


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MAX_ATTEMPTS = 5


# ---------------------------------------------------------------------------
# ASCII Art
# ---------------------------------------------------------------------------

DEADSWITCH_ART = r"""
  ██████╗ ███████╗ █████╗ ██████╗ ███████╗██╗    ██╗██╗████████╗ ██████╗██╗  ██╗
  ██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝██║    ██║██║╚══██╔══╝██╔════╝██║  ██║
  ██║  ██║█████╗  ███████║██║  ██║███████╗██║ █╗ ██║██║   ██║   ██║     ███████║
  ██║  ██║██╔══╝  ██╔══██║██║  ██║╚════██║██║███╗██║██║   ██║   ██║     ██╔══██║
  ██████╔╝███████╗██║  ██║██████╔╝███████║╚███╔███╔╝██║   ██║   ╚██████╗██║  ██║
  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝ ╚══╝╚══╝ ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝
"""

DESTROYED_ART = r"""
  ██████╗ ███████╗███████╗████████╗██████╗  ██████╗ ██╗   ██╗███████╗██████╗ 
  ██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗╚██╗ ██╔╝██╔════╝██╔══██╗
  ██║  ██║█████╗  ███████╗   ██║   ██████╔╝██║   ██║ ╚████╔╝ █████╗  ██║  ██║
  ██║  ██║██╔══╝  ╚════██║   ██║   ██╔══██╗██║   ██║  ╚██╔╝  ██╔══╝  ██║  ██║
  ██████╔╝███████╗███████║   ██║   ██║  ██║╚██████╔╝   ██║   ███████╗██████╔╝
  ╚═════╝ ╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚══════╝╚═════╝
"""

SAFE_ART = r"""
  ███████╗ █████╗ ███████╗███████╗
  ██╔════╝██╔══██╗██╔════╝██╔════╝
  ███████╗███████║███████╗███████╗
  ╚════██║██╔══██║██╔══╝  ██╔══╝  
  ███████║██║  ██║██║     ███████║
  ╚══════╝╚═╝  ╚═╝╚═╝     ███████╗
"""


# ---------------------------------------------------------------------------
# Time presets
# ---------------------------------------------------------------------------

TIME_PRESETS = {
    "1": 10,
    "2": 30,
    "3": 60,
    "4": 300,
    "5": 600,
    "6": 1800,
    "7": 3600,
    "8": 21600,
    "9": 43200,
    "10": 86400,
}


# ---------------------------------------------------------------------------
# Terminal utilities
# ---------------------------------------------------------------------------

def clear_screen() -> None:
    """Clear the terminal."""
    os.system("clear" if platform.system() != "Windows" else "cls")


def get_hidden_input(prompt: str) -> str:
    """Get hidden input using getpass."""
    try:
        return getpass.getpass(prompt)
    except KeyboardInterrupt:
        print("\n[!] cancelled")
        sys.exit(0)


def format_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS or DDd HHh MMm SSs."""
    seconds = max(0, int(seconds))
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if days > 0:
        return f"{days}d {hours:02d}h {minutes:02d}m {secs:02d}s"
    elif hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def select_time() -> float:
    """Show time selection menu and return chosen duration in seconds."""
    print()
    print("[*] select countdown time:")
    print("  1. 10 seconds")
    print("  2. 30 seconds")
    print("  3. 1 minute")
    print("  4. 5 minutes")
    print("  5. 10 minutes")
    print("  6. 30 minutes")
    print("  7. 1 hour")
    print("  8. 6 hours")
    print("  9. 12 hours")
    print("  10. 24 hours")
    print("  11. custom (enter seconds)")
    print()

    try:
        choice = input("choice [1-11]: ").strip()
    except KeyboardInterrupt:
        print("\n[!] cancelled")
        sys.exit(0)

    if choice in TIME_PRESETS:
        return float(TIME_PRESETS[choice])
    elif choice == "11":
        try:
            custom = float(input("enter seconds: "))
            if custom < 5:
                print("[!] minimum 5 seconds")
                return select_time()
            return custom
        except ValueError:
            print("[!] invalid number")
            return select_time()
        except KeyboardInterrupt:
            print("\n[!] cancelled")
            sys.exit(0)
    else:
        print("[!] invalid choice")
        return select_time()


# ---------------------------------------------------------------------------
# Secret storage
# ---------------------------------------------------------------------------

def hash_code(code: str, salt: str) -> str:
    """Hash the code with salt for storage."""
    salted = code + salt
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def verify_code(code: str, salt: str, expected_hash: str) -> bool:
    """Check if entered code matches the expected hash."""
    return hash_code(code, salt) == expected_hash


def store_secret(secret_data: str, code: str, secret_file: str) -> Tuple[str, str]:
    """
    Store secret with salted code hash.
    Returns (salt, code_hash).
    """
    salt = secrets.token_hex(16)
    code_hash = hash_code(code, salt)

    key = hashlib.sha256(code_hash.encode("utf-8")).digest()
    data_bytes = secret_data.encode("utf-8")
    encrypted = bytes(a ^ b for a, b in zip(
        data_bytes,
        key * (len(data_bytes) // len(key) + 1)
    ))

    with open(secret_file, "wb") as f:
        f.write(salt.encode("utf-8"))
        f.write(b"\n")
        f.write(code_hash.encode("utf-8"))
        f.write(b"\n")
        f.write(encrypted)

    return salt, code_hash


def load_secret_metadata(secret_file: str) -> Tuple[str, str]:
    """Load salt and code hash from file header."""
    try:
        with open(secret_file, "rb") as f:
            lines = f.readlines()
            salt = lines[0].strip().decode("utf-8")
            code_hash = lines[1].strip().decode("utf-8")
            return salt, code_hash
    except OSError:
        return "", ""
    except IndexError:
        return "", ""


def destroy_secret(secret_file: str) -> None:
    """Overwrite and delete the secret file."""
    try:
        if os.path.exists(secret_file):
            with open(secret_file, "wb") as f:
                size = os.path.getsize(secret_file)
                f.write(secrets.token_bytes(size))
            os.remove(secret_file)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Deadswitch loop
# ---------------------------------------------------------------------------

def run_deadswitch(secret_file: str, code_hash: str, salt: str, duration: float) -> None:
    """
    Main countdown loop with real-time tracking.
    Correct code fully resets timer.
    5 wrong attempts destroys secret.
    """
    attempts_left = MAX_ATTEMPTS
    start_time = time.time()

    clear_screen()
    print(DEADSWITCH_ART)
    print()
    print(f"[*] deadswitch armed")
    print(f"[*] duration: {format_time(duration)}")
    print(f"[*] max failed attempts: {MAX_ATTEMPTS}")
    print()
    time.sleep(2)

    while True:
        # real elapsed time
        elapsed = time.time() - start_time
        time_left = duration - elapsed

        if time_left <= 0:
            clear_screen()
            print(DESTROYED_ART)
            print()
            print("[!] TIME EXPIRED")
            print("[!] SECRET DESTROYED")
            print()
            destroy_secret(secret_file)
            return

        clear_screen()
        print(DEADSWITCH_ART)
        print()
        print("=" * 70)
        print(f"  TIME REMAINING: {format_time(time_left)}")
        print(f"  FAILED ATTEMPTS LEFT: {attempts_left}")
        print("=" * 70)
        print()

        try:
            code = getpass.getpass("  enter code (hidden): ")
        except KeyboardInterrupt:
            print("\n[!] interrupted")
            break

        # recalculate after input
        elapsed = time.time() - start_time
        time_left = duration - elapsed

        if code.lower() == "quit":
            print("\n[*] deadswitch disarmed")
            print(SAFE_ART)
            return

        if verify_code(code, salt, code_hash):
            start_time = time.time()
            time_left = duration
            print(f"\n[+] CODE ACCEPTED — timer reset to {format_time(time_left)}")
            time.sleep(1)

        else:
            attempts_left -= 1
            print(f"\n[!] WRONG CODE — {attempts_left} attempts remaining")
            time.sleep(1)

            if attempts_left <= 0:
                clear_screen()
                print(DESTROYED_ART)
                print()
                print("[!] MAX FAILED ATTEMPTS REACHED")
                print("[!] SECRET DESTROYED")
                print()
                destroy_secret(secret_file)
                return


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    secret_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".deadswitch_secret")

    clear_screen()
    print(DEADSWITCH_ART)
    print()
    print("DEADSWITCH v3 — Self-Destructing Secret Keeper")
    print("Templar Studios | GPL v3.0")
    print()

    if os.path.exists(secret_file):
        print("[*] existing deadswitch detected")
        print()

        salt, code_hash = load_secret_metadata(secret_file)
        if not salt or not code_hash:
            print("[!] corrupted secret file")
            sys.exit(1)

        code = get_hidden_input("enter code (hidden): ")
        if not code:
            print("[!] no code entered")
            sys.exit(1)

        if not verify_code(code, salt, code_hash):
            print("[!] invalid code")
            sys.exit(1)

        duration = select_time()
        run_deadswitch(secret_file, code_hash, salt, duration)

    else:
        print("[*] no existing secret found")
        print("[*] creating new deadswitch")
        print()

        secret_input = input("enter secret (text or file path): ")
        if not secret_input:
            print("[!] empty secret")
            sys.exit(1)

        if os.path.exists(secret_input) and os.path.isfile(secret_input):
            try:
                with open(secret_input, "r") as f:
                    secret_data = f.read()
                print(f"[*] loaded secret from file: {secret_input}")
            except OSError as e:
                print(f"[!] could not read file: {e}")
                sys.exit(1)
        else:
            secret_data = secret_input
            print("[*] using text as secret")

        print()
        code = get_hidden_input("set unlock code (hidden): ")
        confirm = get_hidden_input("confirm unlock code (hidden): ")

        if code != confirm:
            print("[!] codes do not match")
            sys.exit(1)

        if len(code) < 4:
            print("[!] code too short (min 4 chars)")
            sys.exit(1)

        salt, code_hash = store_secret(secret_data, code, secret_file)
        print(f"[+] secret stored with salted hash")
        print()

        duration = select_time()
        run_deadswitch(secret_file, code_hash, salt, duration)


if __name__ == "__main__":
    main()