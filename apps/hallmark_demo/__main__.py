"""Start a local proof workbench; no workflow launches until the user starts one."""

import argparse
import errno
import threading
import webbrowser
from pathlib import Path

from .client import Client
from .server import DemoServer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("interface", choices=("web", "tui"), nargs="?", default="web")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be 1–65535")
    root = args.root.resolve()
    if not (root / "Makefile").is_file() or not (root / "research/STATE.md").is_file():
        parser.error("--root must be a Hallmark source checkout")
    origin = f"http://127.0.0.1:{args.port}"
    try:
        server = DemoServer(root, args.port)
    except ValueError as error:
        parser.error(str(error) + "; join its existing port or stop that controller first")
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            parser.error("Cannot start the local controller: " + str(error))
        try:
            client = Client(origin)
        except (OSError, ValueError):
            parser.error("Port is occupied by another service; choose --port")
        if client.info["root"] != str(root):
            parser.error("This port belongs to another checkout; choose --port")
        server = None
    if args.interface == "web":
        if not args.no_browser:
            webbrowser.open(origin)
        if server is None:
            print(f"Existing workbench: {origin}")
            return
        print(
            f"Hallmark workbench: {origin}\nCheckout: {root}\n"
            "Ctrl-C stops the server and requests driver cleanup.",
            flush=True,
        )
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            print("\nStopping; retaining evidence and requesting active-run cleanup.", flush=True)
        finally:
            server.server_close()
    else:
        if server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
        from .tui import Workbench

        try:
            Workbench(Client(origin), owns_server=server is not None).run()
        finally:
            if server:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    main()
