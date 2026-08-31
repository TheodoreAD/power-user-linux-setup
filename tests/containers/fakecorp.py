#!/usr/bin/env python3
"""Stand in for the two corporate-network shapes the doctor has to recognise, on localhost:

  :3128  an HTTP proxy that answers every CONNECT with 407 + Proxy-Authenticate: Negotiate, NTLM
  :443   a TLS server presenting a self-signed "Corp Root Inspection CA" certificate

Point /etc/hosts at 127.0.0.1 for whichever hostname you want to look intercepted.
"""

import socket
import ssl
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


def make_cert(directory: Path) -> tuple[str, str]:
    key = directory / "key.pem"
    crt = directory / "crt.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(crt),
            "-days",
            "1",
            "-subj",
            "/CN=Corp Root Inspection CA",
            "-addext",
            "subjectAltName=DNS:pypi.org,DNS:files.pythonhosted.org",
        ],
        check=True,
        capture_output=True,
    )
    return str(crt), str(key)


def proxy_407() -> None:
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 3128))
    server.listen(16)
    while True:
        conn = server.accept()[0]  # peer address unused (typeshed types it loosely)
        try:
            conn.recv(4096)
            conn.sendall(
                b"HTTP/1.1 407 Proxy Authentication Required\r\n"
                b"Proxy-Authenticate: Negotiate\r\n"
                b"Proxy-Authenticate: NTLM\r\n"
                b"Content-Length: 0\r\n\r\n"
            )
        except OSError:
            pass
        finally:
            conn.close()


def tls_server(crt: str, key: str) -> None:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(crt, key)
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 443))
    server.listen(16)
    while True:
        conn = server.accept()[0]  # peer address unused (typeshed types it loosely)
        try:
            with context.wrap_socket(conn, server_side=True) as tls:
                tls.recv(4096)
                tls.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
        except (OSError, ssl.SSLError):
            pass


def main() -> int:
    directory = Path(tempfile.mkdtemp())
    crt, key = make_cert(directory)
    threading.Thread(target=proxy_407, daemon=True).start()
    threading.Thread(target=tls_server, args=(crt, key), daemon=True).start()
    print("fakecorp: proxy on 3128, TLS on 443", flush=True)
    threading.Event().wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
