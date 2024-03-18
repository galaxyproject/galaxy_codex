import pandas as pd
import requests

def extract_public_galaxy_servers_tools() -> dict: 
    """
    Extract the tools from the public Galaxy servers using their API
    """

    to_process = {}
    serverlist = requests.get('https://galaxyproject.org/use/feed.json').json()
    for server in serverlist:
        print(server['title'])
        # We intentionally drop all usegalaxy.eu subdomains. They're all the
        # same as the top level domain and just pollute the supported instances
        # list.
        if '.usegalaxy.eu' in server['url']:
            continue
        # Apparently the french do it too
        if '.usegalaxy.fr' in server['url']:
            continue
        # The aussies will soon
        if '.usegalaxy.org.au' in server['url']:
            continue
        # No test servers permitted
        if 'test.' in server['url']:
            continue
        
        galaxy_url = server['url']
        galaxy_url = galaxy_url.rstrip("/")
        base_url = f"{galaxy_url}/api"

        try:
            r = requests.get(f"{base_url}/tools", params={"in_panel": False}, timeout=5)
            r.raise_for_status()
            r.json()
        except Exception as ex:
            print(f"Exception:\n{ex} \nfor server {galaxy_url}!")
            continue

        to_process[server['title']] = server['url']

    return(to_process)

server_dict = extract_public_galaxy_servers_tools()

s = pd.Series(server_dict)
s.index.name = "Name"
s.name = "urls"
s.to_csv('public_galaxy_servers.csv')
