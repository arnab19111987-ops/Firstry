"""Deliberate vulnerable examples used for golden-path verification of Bandit.

This file contains obvious insecure patterns that static scanners like Bandit
should flag: use of eval on external input, untrusted pickle.loads, and
subprocess with shell=True.
"""
from __future__ import annotations

import subprocess
import pickle


def run_shell_cmd(cmd: str) -> None:
    # Intentionally use shell=True to trigger scanner warnings
    subprocess.Popen(cmd, shell=True)


def insecure_eval(user_input: str) -> object:
    # Dangerous: eval on untrusted input
    return eval(user_input)


def load_untrusted(data: bytes) -> object:
    # Dangerous: untrusted pickle deserialization
    return pickle.loads(data)


if __name__ == "__main__":
    # Exercises the functions when run directly
    run_shell_cmd("echo vulnerable")
    try:
        print(insecure_eval("2 + 2"))
    except Exception:
        pass
    try:
        print(load_untrusted(b"\x80\x04."))
    except Exception:
        pass
