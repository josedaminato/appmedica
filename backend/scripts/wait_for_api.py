"""Espera a que la API responda. Uso: python scripts/wait_for_api.py [base_url]"""
import sys
import time
import urllib.error
import urllib.request

DEFAULT = "http://127.0.0.1:8000/api/v1/health"
MAX_WAIT = 90


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    print(f"Esperando API en {url} ...")
    for i in range(MAX_WAIT):
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    print("OK API lista")
                    return 0
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(1)
        if i % 5 == 4:
            print(f"  ... {i + 1}s")
    print("ERROR: API no respondió a tiempo", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
