#!/usr/bin/env python3
"""
sniff_keys.py — dit QUEL périphérique émet quelle touche.

À lancer en root :   sudo python3 scripts/sniff_keys.py

Sert à savoir si les touches macro (M1..M5) sortent sur un nœud d'entrée
différent des touches normales. Si oui, on peut les remapper sans toucher au
reste du clavier. Sinon, elles sont indistinguables des vraies touches.

Ctrl+C pour quitter.
"""
import glob
import os
import select
import signal
import struct
import sys
import time

FMT = "llHHi"           # input_event 64 bits
SZ = struct.calcsize(FMT)
EV_KEY = 0x01

KEYS = {29: "L-CTRL", 97: "R-CTRL", 42: "L-SHIFT", 54: "R-SHIFT", 56: "L-ALT",
        44: "Z", 45: "X", 30: "A", 47: "V", 46: "C", 16: "Q", 17: "W", 18: "E",
        31: "S", 32: "D", 33: "F", 20: "T", 21: "Y", 19: "R", 34: "G", 35: "H",
        57: "ESPACE", 28: "ENTREE"}

DUREE = 25   # secondes

INTERESTING = ("Rapoo", "CX 2.4G", "Telink")


def device_name(evdev):
    n = os.path.basename(evdev)
    try:
        with open(f"/sys/class/input/{n}/device/name") as f:
            return f.read().strip()
    except OSError:
        return n


def main():
    if os.geteuid() != 0:
        sys.exit("À lancer avec sudo :  sudo python3 scripts/sniff_keys.py")

    fds = {}
    for path in sorted(glob.glob("/dev/input/event*")):
        name = device_name(path)
        if not any(k in name for k in INTERESTING):
            continue
        try:
            f = open(path, "rb", buffering=0)
        except OSError:
            continue
        os.set_blocking(f.fileno(), False)
        fds[f.fileno()] = (f, os.path.basename(path), name)

    if not fds:
        sys.exit("Aucun périphérique clavier trouvé.")

    print("Écoute de :")
    for _, ev, name in fds.values():
        print(f"   {ev:<10} {name}")
    # M1 envoie Ctrl+Z et M5 envoie Ctrl+C : sans ça, le script se suspend ou
    # se termine dès qu'on presse les touches qu'on cherche justement à observer.
    signal.signal(signal.SIGTSTP, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    print(f"\n{DUREE} secondes pour :")
    print("   1. presser M1, M2, M3, M4, M5")
    print("   2. taper quelques lettres normales (asdf) pour comparer\n")

    fin = time.time() + DUREE
    try:
        while time.time() < fin:
            ready, _, _ = select.select(list(fds), [], [], 0.5)
            for fd in ready:
                f, ev, name = fds[fd]
                data = f.read(SZ * 64)
                if not data:
                    continue
                for i in range(0, len(data) - SZ + 1, SZ):
                    _, _, etype, code, value = struct.unpack(FMT, data[i:i + SZ])
                    if etype == EV_KEY and value == 1:      # 1 = appui
                        label = KEYS.get(code, f"code {code}")
                        print(f"  {ev:<10} {name:<38} {label}")
    finally:
        print("\nTerminé.")


if __name__ == "__main__":
    main()
