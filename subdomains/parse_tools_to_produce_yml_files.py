# coding: utf-8
import yaml
import io
import os
import re 
import argparse

parser = argparse.ArgumentParser(description='Create installation yaml files from a Yaml file containing the panel_view/Toolkit data')
parser.add_argument('--tk', action="store", dest='toolkit', help='Path of the toolkit.yaml file') # Toolkit.yaml file
parser.add_argument('--yml-folder', action="store", dest='dest', help='Folder containing the yml files with tool installed in the target instance') # Folder containing the .yml and yml.lock containing the tools installed in the target instance
args = parser.parse_args()

print(args.toolkit)
print(args.dest)

with open(args.toolkit, 'r') as stream:
    data_loaded = yaml.safe_load(stream)

for i in range(3,len(data_loaded['items'])-2):
    section=data_loaded['items'][i]['id']
    name=data_loaded['items'][i]['name']
    f = open(section+".yml", "w")
    f.write("tool_panel_section_label: "+name+"\ntools:\n")
    for j in data_loaded['items'][i]['items']: #for loop on toolkit sections
        path=j['id']
        infos=path.replace('toolshed.g2.bx.psu.edu/repos/',"")
        pattern=re.compile(r"([^\/]+)\/([^\/]+)\/") # extract the owner (group1) and the name of the tool (group2)
        for match in pattern.finditer(infos): #for each tool in the seection
            owner=match.group(1)
            tool=match.group(2)
            installed = os.popen('grep -r "'+tool+'" '+args.dest).read() #verify the tool is not already installed
            if installed=='': ## if tool not installed
                f.write("- name: "+tool+"\n")
                f.write("  owner: "+owner+"\n")
    f.close()
