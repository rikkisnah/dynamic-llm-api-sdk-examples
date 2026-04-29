"""Print the next free TCP port at or after a starting value.

Used by the Makefile `ui`/`run` targets so a busy default port (e.g. 8501)
falls back to the next available one instead of crashing Streamlit.
"""

from __future__ import annotations

import argparse
import socket
import sys


def is_port_free(port: int, *, host: str = "127.0.0.1") -> bool:
    """Return True when `host:port` can be bound right now."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def main(argv: list[str] | None = None) -> int:
    """Print the first free port in `[start, start+span)` or fall back to start."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=8501)
    parser.add_argument("--span", type=int, default=50)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)
    for port in range(args.start, args.start + args.span):
        if is_port_free(port, host=args.host):
            print(port)
            return 0
    sys.stderr.write(
        f"find_free_port: no free port in [{args.start}, {args.start + args.span}); "
        f"falling back to {args.start}.\n"
    )
    print(args.start)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
