#!/usr/bin/env python

import argparse
import base64

from github import Github

def get_string_content(cf):
    '''
    Get string of the content from a ContentFile

    cf: ContentFile object
    '''
    return str(base64.b64decode(cf.content))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract a GitHub project to CSV')
    parser.add_argument('--api', '-a', required=True, help="GitHub access token")
    parser.add_argument('--output', '-o', required=True, help="Output filepath")
    args = parser.parse_args()

    # connect to GitHub
    g = Github(args.api)

    # get tool GitHub repository
    repo = g.get_user("galaxyproject").get_repo("planemo-monitor")
    repo_list = []
    for i in range(1, 5):
        repo_f = repo.get_contents(f"repositories0{i}.list")
        print(get_string_content(repo_f))


