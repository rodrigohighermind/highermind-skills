#!/usr/bin/env python3
"""Sobe um ou mais servidores, espera as portas abrirem, roda um comando e derruba tudo.

Uso:
    python3 with_server.py --server "npm run dev" --port 3000 -- python3 shot.py
    python3 with_server.py \\
        --server "cd api && uv run app.py" --port 8000 \\
        --server "cd web && npm run dev" --port 3000 \\
        -- python3 shot.py

Logs de cada servidor vão para --log-dir (default: diretório temporário), nunca para um
PIPE sem leitor, que trava servidor verboso. Exit code é o do comando; 3 se um servidor
não subir no timeout.

"""

from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import IO

EXIT_SERVER_TIMEOUT = 3


def wait_for_port(port: int, timeout: float, process: subprocess.Popen[bytes]) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=8)
    except ProcessLookupError:
        return
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--server", action="append", required=True, help="comando do servidor (repetível)")
    parser.add_argument("--port", action="append", type=int, required=True, help="porta de cada servidor, na mesma ordem")
    parser.add_argument("--timeout", type=float, default=60.0, help="segundos para cada porta abrir")
    parser.add_argument("--log-dir", type=Path, default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER, help="-- comando a rodar com os servidores no ar")
    args = parser.parse_args()

    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("informe o comando depois de --")
    if len(args.server) != len(args.port):
        parser.error("cada --server precisa de um --port")

    log_dir: Path = args.log_dir or Path(tempfile.mkdtemp(prefix="with-server-"))
    log_dir.mkdir(parents=True, exist_ok=True)
    processes: list[subprocess.Popen[bytes]] = []
    logs: list[IO[bytes]] = []
    try:
        for index, (server, port) in enumerate(zip(args.server, args.port)):
            log_path = log_dir / f"server-{index}-{port}.log"
            log: IO[bytes] = log_path.open("wb")
            logs.append(log)
            process = subprocess.Popen(
                server, shell=True, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
            )
            processes.append(process)
            print(f"[with_server] {server!r} → :{port} (log {log_path})", file=sys.stderr)
            if not wait_for_port(port, args.timeout, process):
                print(f"[with_server] FAIL · :{port} não abriu em {args.timeout:.0f}s. Ver {log_path}", file=sys.stderr)
                return EXIT_SERVER_TIMEOUT
        return subprocess.run(command, check=False).returncode
    finally:
        for process in reversed(processes):
            stop(process)
        for log in logs:
            log.close()


if __name__ == "__main__":
    sys.exit(main())
