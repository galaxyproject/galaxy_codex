import argparse

import pandas as pd
import requests


def get_public_galaxy_servers(output: str) -> None:
    """
    Get public galaxy servers, that can be queried for tools using their API

    :param output: path to output the server list
    """

    to_process = {}
    serverlist = requests.get("https://galaxyproject.org/use/feed.json").json()
    for server in serverlist:

        print(server["title"])
        # We intentionally drop all usegalaxy.eu subdomains. They're all the
        # same as the top level domain and just pollute the supported instances
        # list.
        if ".usegalaxy.eu" in server["url"]:
            continue
        # Apparently the french do it too
        if ".usegalaxy.fr" in server["url"]:
            continue
        # The aussies will soon
        if ".usegalaxy.org.au" in server["url"]:
            continue
        # No test servers permitted
        if "test." in server["url"]:
            continue

        galaxy_url = server["url"]
        galaxy_url = galaxy_url.rstrip("/")
        base_url = f"{galaxy_url}/api"

        try:
            r = requests.get(f"{base_url}/tools", params={"in_panel": False}, timeout=30)
            r.raise_for_status()
            r.json()
        except Exception as ex:
            print(f"Exception:\n{ex} \nfor server {galaxy_url}!")
            continue

        to_process[server["title"]] = server["url"]

        s = pd.Series(to_process)
        s.index.name = "name"
        s.name = "urls"
        s.to_csv(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create list of public available galaxy servers")

    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Path to output TSV file with the servers",
    )

    args = parser.parse_args()
    get_public_galaxy_servers(args.output)
