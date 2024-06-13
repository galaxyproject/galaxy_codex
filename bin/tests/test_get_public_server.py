######################################
# Initial start for function based unit tests
# need to set this up using a proper testing framework
######################################

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from extract_galaxy_tools import (
    check_tools_on_servers,
    USEGALAXY_SERVER_URLS,
)

server_url = USEGALAXY_SERVER_URLS["UseGalaxy.eu"]
tool_ids = ["abricate"]

count = check_tools_on_servers(tool_ids, server_url)
print(count)

tool_ids = ["bla"]
count = check_tools_on_servers(tool_ids, server_url)
print(count)

server_url = "https://jolo.eu"
tool_ids = ["bla"]
count = check_tools_on_servers(tool_ids, server_url)
print(count)
