import argparse
import concurrent.futures
import sys
import time

import pandas as pd
import requests


SKIP_PATTERNS = [
    "hub.docker.com",
    "github.com",
    "docker.io",
    "readthedocs",
    "aws.amazon",
    "nectar.org",
    "docker",
]

GALAXY_SUBDOMAINS = [
    ".usegalaxy.eu",
    ".usegalaxy.fr",
    ".usegalaxy.org.au",
]


def is_likely_galaxy_url(url: str) -> bool:
    """Skip entries that are clearly not Galaxy instance URLs."""
    url_lower = url.lower()
    for pattern in SKIP_PATTERNS:
        if pattern in url_lower:
            return False
    return True


def check_server(title: str, url: str, session: requests.Session, timeout: int) -> tuple[str, str, bool]:
    """Check if a server has a working Galaxy API. Returns (title, url, ok)."""
    galaxy_url = url.rstrip("/")
    try:
        r = session.get(
            f"{galaxy_url}/api/tools",
            params={"in_panel": False},
            timeout=timeout,
        )
        r.raise_for_status()
        r.json()
        return (title, galaxy_url, True)
    except Exception as ex:
        return (title, galaxy_url, False)


def get_public_galaxy_servers(output: str, workers: int = 20, timeout: int = 15) -> None:
    """
    Get public galaxy servers that can be queried for tools using their API.

    :param output: path to output the server list TSV
    :param workers: number of parallel workers
    :param timeout: request timeout in seconds
    """
    feed = requests.get("https://galaxyproject.org/use/feed.json", timeout=30).json()

    candidates: list[tuple[str, str]] = []
    for server in feed:
        url = server["url"]
        title = server["title"]

        if not is_likely_galaxy_url(url):
            continue
        if any(sub in url for sub in GALAXY_SUBDOMAINS):
            continue
        if "test." in url:
            continue

        candidates.append((title, url))

    print(f"Checking {len(candidates)} candidate servers with {workers} workers...", file=sys.stderr)

    found: dict[str, str] = {}
    start = time.time()
    with requests.Session() as session:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(check_server, title, url, session, timeout)
                for title, url in candidates
            ]
            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                title, url, ok = future.result()
                status = "OK" if ok else "FAIL"
                elapsed = time.time() - start
                print(f"[{elapsed:6.1f}s] ({i:3d}/{len(candidates)}) {status:4s} {title}", file=sys.stderr)
                if ok:
                    found[title] = url

    print(f"\nFound {len(found)} working servers in {time.time() - start:.1f}s", file=sys.stderr)

    s = pd.Series(found)
    s.index.name = "name"
    s.name = "url"
    s.to_csv(output, sep="\t")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create list of public available galaxy servers")
    parser.add_argument(
        "--output", "-o", required=True,
        help="Path to output TSV file with the servers",
    )
    parser.add_argument(
        "--workers", type=int, default=20,
        help="Number of parallel workers (default: 20)",
    )
    parser.add_argument(
        "--timeout", type=int, default=15,
        help="Request timeout in seconds (default: 15)",
    )
    args = parser.parse_args()
    get_public_galaxy_servers(args.output, workers=args.workers, timeout=args.timeout)
