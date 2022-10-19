#!/usr/bin/env python

import argparse
import base64

from github import Github

def get_string_content(cf):
    '''
    Get string of the content from a ContentFile

    param cf: ContentFile object
    '''
    return base64.b64decode(cf.content).decode('ascii')


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
    Get a GitHub repository from an URL

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
    print(u_split)
    return g.get_user(u_split[-2]).get_repo(u_split[-1])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract a GitHub project to CSV')
    parser.add_argument('--api', '-a', required=True, help="GitHub access token")
    parser.add_argument('--output', '-o', required=True, help="Output filepath")
    args = parser.parse_args()

    # connect to GitHub
    g = Github(args.api)
    # get list of GitHub repositories to parse
    repo_list = get_tool_github_repositories(g)
    # 
    for r in repo_list:
        print(r)
        if "github" not in r:
            continue
        repo = get_github_repo(r, g)
        


