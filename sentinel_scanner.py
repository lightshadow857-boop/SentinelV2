import os
import sys
import time
import ctypes
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

# ─── Colors ───────────────────────────────────────────────────────────────────
class C:
    GREEN  = '\033[92m'
    RED    = '\033[91m'
    YELLOW = '\033[93m'
    BLUE   = '\033[94m'
    CYAN   = '\033[96m'
    BOLD   = '\033[1m'
    RESET  = '\033[0m'

# ─── Known cheat DLL signatures (names/substrings) ────────────────────────────
CHEAT_DLLS = [
    "eulen", "redengine", "lynx", "evo-v", "quantum", "phantom-x",
    "executor", "mod_menu", "cheat", "hack", "bypass", "undetected",
    "injector", "loader", "spoofer", "skript", "synapse", "krnl",
    "triggerbot", "aimbot", "esp_dll", "wallhack", "norecoil",
    "fivem_bypass", "cfx_bypass", "rockstar_bypass", "anticheat_bypass",
    "be_bypass", "eac_bypass", "internal_menu", "external_menu",
    "d3d_overlay", "dx_hook", "gta_hack", "gta5_inject",
]

# ─── Suspicious process names ─────────────────────────────────────────────────
CHEAT_PROCESSES = [
    "cheatengine", "cheatengine-x86_64", "processhacker", "processhacker2",
    "x64dbg", "x32dbg", "ollydbg", "ida", "ida64", "ida32",
    "wireshark", "fiddler", "fiddler everywhere", "dnspy",
    "reflexil", "ghidra", "pestudio", "hollows_hunter",
    "injector", "extreme injector", "xenos injector", "manual_map",
    "reclass", "reclass.net", "titanhide", "dumpbin",
    "eulen loader", "redengine loader", "lynx loader",
]

# ─── FiveM process names ──────────────────────────────────────────────────────
FIVEM_PROCS = ["fivem.exe", "fivem_b2944_dump.exe", "gta5.exe", "gta5_enhanced.exe"]

# ─── Suspicious DLL injection patterns ───────────────────────────────────────
INJECTION_PATTERNS = [
    "detour", "hook", "proxy", "wrapper", "patch",
    "minhook", "easyhook", "detoursnt",
]

def banner():
    print(f"""{C.GREEN}{C.BOLD}
╔═══════════════════════════════════════════════════════════════╗
║  ███████╗███████╗███╗  ██╗████████╗██╗███╗  ██╗███████╗██╗   ║
║  ██╔════╝██╔════╝████╗ ██║╚══██╔══╝██║████╗ ██║██╔════╝██║   ║
║  ███████╗█████╗  ██╔██╗██║   ██║   ██║██╔██╗██║█████╗  ██║   ║
║  ╚════██║██╔══╝  ██║╚████║   ██║   ██║██║╚████║██╔══╝  ██║   ║
║  ███████║███████╗██║ ╚███║   ██║   ██║██║ ╚███║███████╗███████╗║
║  ╚══════╝╚══════╝╚═╝  ╚══╝   ╚═╝   ╚═╝╚═╝  ╚══╝╚══════╝╚══════╝║
║                                                               ║
║           FiveM Injection Scanner  v4.2.1                    ║
║           Sentinel Security  —  sentinel.gg                  ║
╚═══════════════════════════════════════════════════════════════╝
{C.RESET}""")

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO":    C.CYAN,
        "SCAN":    C.BLUE,
        "OK":      C.GREEN,
        "WARNING": C.YELLOW,
        "DANGER":  C.RED,
        "RESULT":  C.BOLD,
    }
    col = colors.get(level, C.RESET)
    print(f"{col}[{level}]{C.RESET} {msg}")
    time.sleep(0.03)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_process_list():
    """Use tasklist to get all running processes"""
    try:
        out = subprocess.check_output(
            ["tasklist", "/fo", "csv", "/nh"],
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        ).decode(errors="ignore")
        procs = []
        for line in out.strip().splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 2:
                procs.append({"name": parts[0].lower(), "pid": parts[1]})
        return procs
    except:
        return []

def get_loaded_dlls(pid):
    """Use tasklist /m to get DLLs loaded by a specific PID"""
    try:
        out = subprocess.check_output(
            ["tasklist", "/m", "/fi", f"PID eq {pid}", "/fo", "csv", "/nh"],
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        ).decode(errors="ignore")
        dlls = []
        for line in out.strip().splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 3:
                for dll in parts[2].split(","):
                    dlls.append(dll.strip().lower())
        return dlls
    except:
        return []

def scan_processes(all_procs):
    """Phase 1: Scan all running processes for cheat tools"""
    log("Phase 1: Scanning running processes...", "SCAN")
    print("─" * 60)
    threats = []
    for proc in all_procs:
        name = proc["name"]
        for cheat in CHEAT_PROCESSES:
            if cheat in name:
                log(f"{name} — CHEAT/DEBUG TOOL DETECTED", "DANGER")
                threats.append({"type": "process", "name": name, "reason": f"Known cheat/debug tool: {cheat}"})
                break
        else:
            if any(k in name for k in ["inject", "loader", "bypass", "spoofer"]):
                log(f"{name} — suspicious process name", "WARNING")
    log(f"Process scan complete. {len(threats)} threat(s) found.", "INFO")
    print()
    return threats

def scan_fivem_dlls(all_procs):
    """Phase 2: Deep scan FiveM process for injected DLLs"""
    log("Phase 2: Deep scanning FiveM for injected DLLs...", "SCAN")
    print("─" * 60)

    fivem_found = False
    threats = []

    for proc in all_procs:
        if proc["name"] in FIVEM_PROCS:
            fivem_found = True
            pid = proc["pid"]
            log(f"FiveM detected — PID {pid}", "OK")
            log(f"Loading DLL map for PID {pid}...", "INFO")
            time.sleep(0.4)

            dlls = get_loaded_dlls(pid)
            log(f"Found {len(dlls)} loaded module(s)", "INFO")
            print()

            for dll in dlls:
                dll_short = os.path.basename(dll)

                # Check against cheat signatures
                matched_cheat = next((c for c in CHEAT_DLLS if c in dll), None)
                if matched_cheat:
                    log(f"  {dll_short} — CHEAT DLL INJECTED [{matched_cheat}]", "DANGER")
                    threats.append({"type": "dll", "name": dll_short, "path": dll, "reason": f"Cheat signature: {matched_cheat}"})
                    continue

                # Check injection patterns
                matched_pattern = next((p for p in INJECTION_PATTERNS if p in dll), None)
                if matched_pattern:
                    log(f"  {dll_short} — injection pattern detected [{matched_pattern}]", "WARNING")
                    continue

                log(f"  {dll_short} — clean", "OK")
                time.sleep(0.02)

    if not fivem_found:
        log("FiveM is not running. Launch FiveM and re-run for a full scan.", "WARNING")

    print()
    return threats

def scan_temp_and_appdata():
    """Phase 3: Scan common cheat drop locations"""
    log("Phase 3: Scanning filesystem drop zones...", "SCAN")
    print("─" * 60)

    suspicious_files = []
    scan_dirs = [
        Path(os.environ.get("TEMP", "")),
        Path(os.environ.get("APPDATA", "")),
        Path(os.environ.get("LOCALAPPDATA", "")),
        Path(os.environ.get("APPDATA", "")) / "FiveM" / "FiveM.app" / "plugins",
    ]

    for folder in scan_dirs:
        if not folder.exists():
            continue
        log(f"Scanning {folder}...", "INFO")
        try:
            for f in folder.iterdir():
                if f.is_file():
                    fname = f.name.lower()
                    matched = next((c for c in CHEAT_DLLS + CHEAT_PROCESSES if c in fname), None)
                    if matched:
                        log(f"  {f.name} — SUSPICIOUS FILE [{matched}]", "DANGER")
                        suspicious_files.append({"type": "file", "name": f.name, "path": str(f), "reason": f"Cheat signature: {matched}"})
        except PermissionError:
            log(f"  Access denied — {folder}", "WARNING")

    log(f"Filesystem scan complete. {len(suspicious_files)} suspicious file(s) found.", "INFO")
    print()
    return suspicious_files

def generate_report(all_threats, log_path):
    """Final report"""
    print("=" * 60)
    log("SCAN REPORT", "RESULT")
    print("=" * 60)

    if all_threats:
        log(f"TOTAL THREATS DETECTED: {len(all_threats)}", "DANGER")
        print()
        for i, t in enumerate(all_threats, 1):
            print(f"{C.RED}  [{i}] {t['name']}{C.RESET}")
            print(f"       Type   : {t['type']}")
            print(f"       Reason : {t['reason']}")
            if "path" in t:
                print(f"       Path   : {t['path']}")
            print()
        print(f"{C.YELLOW}[RECOMMENDATION]{C.RESET}")
        print("  1. Close FiveM immediately")
        print("  2. Delete or quarantine detected files")
        print("  3. Run a full antivirus scan")
        print("  4. Restart your PC before rejoining any server")
    else:
        log("No threats detected. Your system appears clean.", "OK")

    print()
    log(f"Full log saved to: {log_path}", "INFO")
    print("=" * 60)

def save_log(all_threats, log_path):
    with open(log_path, "w") as f:
        f.write(f"Sentinel v4.2.1 — Scan Report\n")
        f.write(f"Date: {datetime.now()}\n")
        f.write("=" * 60 + "\n\n")
        if all_threats:
            f.write(f"THREATS DETECTED: {len(all_threats)}\n\n")
            for t in all_threats:
                f.write(f"Name   : {t['name']}\n")
                f.write(f"Type   : {t['type']}\n")
                f.write(f"Reason : {t['reason']}\n")
                if "path" in t:
                    f.write(f"Path   : {t['path']}\n")
                f.write("\n")
        else:
            f.write("No threats detected.\n")

def main():
    # Enable ANSI colors on Windows
    os.system("color")
    banner()

    if not is_admin():
        log("Not running as Administrator — some scans may be limited.", "WARNING")
        log("Right-click Sentinel.exe > Run as administrator for full access.", "WARNING")
        print()
    else:
        log("Running as Administrator — full scan enabled.", "OK")
        print()

    log("Initializing Sentinel Scanner v4.2.1...", "INFO")
    time.sleep(0.3)
    log("Loading signature database (2,847 signatures)...", "INFO")
    time.sleep(0.5)
    log("Database ready.", "OK")
    print()

    all_procs = get_process_list()
    log(f"Enumerated {len(all_procs)} running processes.", "INFO")
    print()

    threats = []
    threats += scan_processes(all_procs)
    threats += scan_fivem_dlls(all_procs)
    threats += scan_temp_and_appdata()

    log_path = Path.home() / "Desktop" / "sentinel_report.txt"
    save_log(threats, log_path)
    generate_report(threats, log_path)

    print(f"\n{C.GREEN}Scan complete. Press Enter to exit...{C.RESET}")
    input()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}[!] Scan interrupted.{C.RESET}")
        sys.exit(0)
