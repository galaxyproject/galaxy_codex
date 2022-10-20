#!/usr/bin/env python

import argparse
import base64
from unicodedata import category
import pandas as pd
import yaml
import xml.etree.ElementTree as et

from github import Github
from pathlib import Path


def read_file(filepath):
    '''
    Read an optional file with 1 element per line

    :param filepath: path to a file
    '''

    fp = Path(filepath)
    if fp.is_file():
        with fp.open('r') as f:
            return [x.rstrip() for x in f.readlines()]


def get_string_content(cf):
    '''
    Get string of the content from a ContentFile

    param cf: GitHub ContentFile object
    '''
    return base64.b64decode(cf.content).decode('utf-8')


def get_tool_github_repositories(g):
    '''
    Get list of tool GitHub repositories to parse

    param g: GitHub instance
    '''
    repo = g.get_user("galaxyproject").get_repo("planemo-monitor")
    repo_list = []
    for i in range(1, 5):
        repo_f = repo.get_contents(f"repositories0{i}.list")
        repo_l = get_string_content(repo_f).rstrip()
        repo_list += repo_l.split("\n")
    return(repo_list)


def get_github_repo(url, g):
    '''
    Get a GitHub Repository object from an URL

    param url: URL to a GitHub repository
    param g: GitHub instance
    '''
    if not url.startswith("https://github.com/"):
        raise ValueError
    if url.endswith("/"):
        url = url[:-1]
    if url.endswith(".git"):
        url = url[:-4]
    u_split = url.split("/")
    return g.get_user(u_split[-2]).get_repo(u_split[-1])


def get_shed_attribute(attrib, shed_content):
    '''
    Get a shed attribute

    :param attrib: attribute to extract
    :param shed_content: content of the .shed.yml
    '''
    if attrib in shed_content:
        return shed_content[attrib]
    else:
        return None


def get_biotools(el):
    '''
    Get bio.tools information

    :param el: Element object
    '''
    xrefs = el.find('xrefs')
    if xrefs is not None:
        xref = xrefs.find('xref')
        if xref is not None and xref.attrib['type'] == 'bio.tools':
            return xref.text
    return None


def get_conda_package(el):
    '''
    Get conda package information

    :param el: Element object
    '''
    reqs = el.find('requirements')
    if reqs is not None:
        req = reqs.find('requirement')
        if req is not None:
            return req.text
        #for req in reqs.findall('requirement'):
        #    if 'version' in req.attrib:
        #        if req.attrib['version'] == '@VERSION@' or req.attrib['version'] == '@TOOL_VERSION@':
        #            return req.text
        #        elif req.attrib['version']
        #    elif 'version' in req.attrib:
        #        return req.text
        #    else:
        #        return req.text
    return None


def get_tool_metadata(tool, repo):
    '''
    Get tool information
    - Check the `.shed.yaml` file
    - Extract metadata from the `.shed.yaml`
    - Filter for specific ToolShed categories
    - Extract the requirements in the macros or xml file to get tool version supported in Galaxy
    - Extract bio.tools information if available in the macros or xml

    param tool: GitHub ContentFile object
    param repo: GitHub Repository object
    '''
    metadata = {
        'Description': None,
        'Toolshed Categories': None,
        'Source': None,
        'ToolShed id': None,
        'Wrapper owner': None,
        'Wrapper source': None,
        'Wrapper version': None,
        'bio.tool id': None,
        'conda id': None,
    }
    # extract .shed.yml and check macros.xml
    for file in repo.get_contents(tool.path):
        if file.name == '.shed.yml':
            file_content = get_string_content(file)
            yaml_content = yaml.load(file_content, Loader=yaml.FullLoader)

            metadata['Description'] = get_shed_attribute('description', yaml_content)
            metadata['Toolshed Categories'] = get_shed_attribute('categories', yaml_content)
            metadata['ToolShed id'] = get_shed_attribute('name', yaml_content)
            metadata['Wrapper owner'] = get_shed_attribute('owner', yaml_content)
            metadata['Wrapper source'] = get_shed_attribute('remote_repository_url', yaml_content)
            if 'homepage_url' in yaml_content:
                metadata['Source'] = yaml_content['homepage_url']
        elif 'macro' in file.name and file.name.endswith('xml'):
            print(file.path)
            file_content = get_string_content(file)
            root = et.fromstring(file_content)
            for child in root:
                if 'name' in child.attrib:
                    if child.attrib['name'] == '@TOOL_VERSION@' or child.attrib['name'] == '@VERSION@':
                        metadata['Wrapper version'] = child.text
                    elif child.attrib['name'] == 'bio_tools':
                        metadata['bio.tool id'] = get_biotools(child)
                    elif child.attrib['name'] == 'requirements':
                        metadata['conda id'] = get_conda_package(child)
    # parse XML file if metadata not found in the macro file
    if metadata['Wrapper version'] is None or metadata['bio.tool id'] is None or metadata['conda id'] is None:
        for file in repo.get_contents(tool.path):
            if file.name.endswith('xml') and 'macro' not in file.name:
                print(file.path)
                file_content = get_string_content(file)
                root = et.fromstring(file_content)
                # version
                if metadata['Wrapper version'] is None:
                    version = root.attrib['version']
                    if 'VERSION@' not in version:
                        metadata['Wrapper version'] = version
                    else:
                        macros = root.find('macros')
                        if macros is not None:
                            for child in macros:
                                if 'name' in child.attrib and (child.attrib['name'] == '@TOOL_VERSION@' or child.attrib['name'] == '@VERSION@'):
                                    metadata['Wrapper version'] = child.text
                # bio.tools
                if metadata['bio.tool id'] is None:
                    biotools = get_biotools(root)
                    if biotools is not None:
                        metadata['bio.tool id'] = biotools
                # conda package
                if metadata['conda id'] is None:
                    reqs = get_conda_package(root)
                    if reqs is not None:
                        metadata['conda id'] = reqs
    return metadata


def parse_tools(repo, ts_cat, excluded_tools):
    '''
    Parse tools in a GitHub repository to expact

    param repo: GitHub Repository object
    param ts_cat: list of ToolShed categories to keep in the extraction
    param excluded_tools: list of tools to skip
    '''
    tools = []
    for tool in repo.get_contents("tools"):
        if tool.name in excluded_tools:
            continue
        if tool.type == 'dir':
            print(tool.name)
            metadata = get_tool_metadata(tool, repo)
            # filter categories
            if metadata['Toolshed Categories'] is not None and ts_cat is not None:
                to_keep = False
                for cat in metadata['Toolshed Categories']:
                    if cat in ts_cat:
                        to_keep = True
                if to_keep:
                    tools.append(metadata)
                    print("added")
                    print(metadata)
            else:
                tools.append(metadata)
                print("added")
                print(metadata)
    return tools


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract a GitHub project to CSV')
    parser.add_argument('--api', '-a', required=True, help="GitHub access token")
    parser.add_argument('--output', '-o', required=True, help="Output filepath")
    parser.add_argument('--categories', '-c', help="Path to a file with ToolShed category to keep in the extraction (one per line)")
    parser.add_argument('--excluded', '-e', help="Path to a file with ToolShed ids of tools to exclude (one per line)")
    args = parser.parse_args()

    # connect to GitHub
    g = Github(args.api)
    # get list of GitHub repositories to parse
    repo_list = get_tool_github_repositories(g)

    # get categories and tools to exclude
    categories = read_file(args.categories)
    excl_tools = read_file(args.excluded)
    print(categories)
    print(excl_tools)

    # parse tools in GitHub repositories to extract metada and filter by TS categories
    tools = []
    for r in repo_list:
        if r != 'https://github.com/galaxyproject/tools-iuc':
            continue
        print(r)
        if "github" not in r:
            continue
        repo = get_github_repo(r, g)
        tools += parse_tools(repo, categories, excl_tools)

    # export tool metadata to tsv output file
    df = pd.DataFrame(tools)
    df.to_csv(args.output, sep="\t", index=False)

