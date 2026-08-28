#!/usr/bin/env python3
"""
Deadswitch - self-destructing secret keeper
Part of Templar Studios | GPL v3.0

Stores a secret with a countdown timer. Code input is hidden,
salted, and hashed. After 5 failed attempts, the secret is
permanently destroyed.

Works fully in ish, a-shell, linux, macOS.

Usage:
  deadswitch.py
"""

import sys
import os
import time
import hashlib
import secrets
import getpass
import platform
from typing import Optional


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

RESET_TIME = 30.0
MIN_TIME = 11.5
MAX_TIME = 90.0
MAX_ATTEMPTS = 5
DISPLAY_REFRESH = 0.2


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


# ---------------------------------------------------------------------------
# Secret storage
# ---------------------------------------------------------------------------

def hash_code(code: str, salt: str) -> str:
    """Hash the code with salt for storage."""
    salted = code + salt
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def store_secret(secret_data: str, code: str, secret_file: str) -> str:
    """
    Store secret with salted code hash.
    Returns the salt so it can be kept in memory.
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
        f.write(encrypted)

    return salt


def retrieve_secret(code: str, salt: str, secret_file: str) -> str:
    """Retrieve and decrypt secret data."""
    try:
        with open(secret_file, "rb") as f:
            encrypted = f.read()
    except OSError:
        return ""

    code_hash = hash_code(code, salt)
    key = hashlib.sha256(code_hash.encode("utf-8")).digest()
    decrypted = bytes(a ^ b for a, b in zip(
        encrypted,
        key * (len(encrypted) // len(key) + 1)
    ))
    return decrypted.decode("utf-8", errors="replace")


def verify_code(code: str, salt: str, expected_hash: str) -> bool:
    """Check if entered code matches the expected hash."""
    return hash_code(code, salt) == expected_hash


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
# Countdown timer
# ---------------------------------------------------------------------------

def format_time(seconds: float) -> str:
    """Format seconds as MM:SS.m"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 10)
    return f"{minutes:02d}:{secs:02d}.{millis}"


def run_deadswitch(secret_file: str, code_hash: str, salt: str) -> None:
    """
    Main countdown loop.
    Code is hidden, salted, hashed, and verified.
    """
    time_left = RESET_TIME
    attempts_left = MAX_ATTEMPTS

    print(DEADSWITCH_ART)
    print()
    print(f"[*] deadswitch armed")
    print(f"[*] timer started: {RESET_TIME}s")
    print(f"[*] max failed attempts: {MAX_ATTEMPTS}")
    print()

    while True:
        clear_screen()
        print(DEADSWITCH_ART)
        print()
        print("=" * 70)
        print(f"  TIME REMAINING: {format_time(time_left)}")
        print(f"  FAILED ATTEMPTS LEFT: {attempts_left}")
        print("=" * 70)
        print()

        try:
            code = getpass.getpass(f"  enter code (hidden): ")
        except KeyboardInterrupt:
            print("\n[!] interrupted")
            break

        if code.lower() == "quit":
            print("\n[*] deadswitch disarmed")
            print(SAFE_ART)
            return

        if verify_code(code, salt, code_hash):
            # correct code — reset timer
            if time_left < MIN_TIME:
                time_left = RESET_TIME
            else:
                time_left = min(time_left + RESET_TIME, MAX_TIME)

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

        # countdown
        time_left -= 1.0
        if time_left <= 0:
            clear_screen()
            print(DESTROYED_ART)
            print()
            print("[!] TIME EXPIRED")
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
    print("DEADSWITCH — Self-Destructing Secret Keeper")
    print("Templar Studios | GPL v3.0")
    print()

    if os.path.exists(secret_file):
        print("[*] existing deadswitch detected")
        print()

        # need salt from file header
        try:
            with open(secret_file, "rb") as f:
                salt = f.readline().strip().decode("utf-8")
        except OSError:
            print("[!] could not read secret file")
            sys.exit(1)

        code = get_hidden_input("enter code (hidden): ")
        if not code:
            print("[!] no code entered")
            sys.exit(1)

        # verify code before starting
        # we need the hash - since we store only salt in header,
        # we need to check against the stored secret data
        # for simplicity, we store the code hash too

        # fix: re-read the full file format
        try:
            with open(secret_file, "rb") as f:
                lines = f.readlines()
                salt = lines[0].strip().decode("utf-8")
                stored_hash = lines[1].strip().decode("utf-8")
                encrypted = b"".join(lines[2:])
        except OSError:
            print("[!] could not read secret file")
            sys.exit(1)

        if not verify_code(code, salt, stored_hash):
            print("[!] invalid code")
            sys.exit(1)

        run_deadswitch(secret_file, stored_hash, salt)

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

        salt = secrets.token_hex(16)
        code_hash = hash_code(code, salt)
        store_secret(secret_data, code, secret_file, salt, code_hash)

        print(f"[+] secret stored with salted hash")
        print()

        run_deadswitch(secret_file, code_hash, salt)


def store_secret(secret_data: str, code: str, secret_file: str,
                 salt: str, code_hash: str) -> None:
    """Store secret with salt and hash in file header."""
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


if __name__ == "__main__":
    main()