"""Build URLs for each Lab page for Labs that have been changed in this PR.

Test each URL to see if it returns a 200 status code, and post the results
in a PR comment.
"""

import os
import sys
from github import Github
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

COMMENT_TITLE_TEMPLATE = "Preview changes to {lab_name} Lab <!--=-->"
URL_TEMPLATE = (
    "https://labs.usegalaxy.org.au"
    "/?content_root=https://github.com/{repo}"
    "/blob/{branch_name}/{lab_content_path}"
    "&cache=false"
)
TRY_FILES = [
    'base.yml',
    'usegalaxy.eu.yml',
    'usegalaxy.org.yml',
    'usegalaxy.org.au.yml',
]

# Environment variables from GitHub Actions
PR_NUMBER = int(os.environ["PR_NUMBER"])
BRANCH_NAME = os.environ["BRANCH_NAME"]
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BASE_REPO = os.getenv("BASE_REPO")
HEAD_REPO = os.getenv("HEAD_REPO")


def get_comment(pull_request, id_string):
    """Fetches PR comments and scans for the COMMENT_TITLE_TEMPLATE."""
    for comment in pull_request.get_issue_comments():
        if id_string in comment.body:
            return comment
    return None


def create_or_update_comment(lab_name, body_md):
    """Creates or updates a comment for the given lab name.

    Checks for an existing comment by looking for the COMMENT_TITLE_TEMPLATE
    in existing comments.
    """
    divider = "\n\n" + '-' * 80 + '\n\n'
    print("Posting comment:", divider, body_md.strip(' \n'), divider)
    title_string = COMMENT_TITLE_TEMPLATE.format(lab_name=lab_name)
    gh = Github(GITHUB_TOKEN)
    print("Getting base repo:", BASE_REPO)
    repo = gh.get_repo(BASE_REPO)
    pull_request = repo.get_pull(PR_NUMBER)
    comment = get_comment(pull_request, title_string)
    if comment:
        comment.edit(body_md)
    else:
        pull_request.create_issue_comment(body_md)


def post_lab_links(lab_name):
    """Iterate through each YAML root file for the given lab name.
    For files that exist, build a URL for that Lab page, check the HTTP status
    code and post the URLs with pass/fail status as a comment on the PR.
    """
    success = True
    title_string = COMMENT_TITLE_TEMPLATE.format(lab_name=lab_name)
    comment = f"### {title_string}\n\n"
    test_paths = [
        f'communities/{lab_name}/lab/{f}'
        for f in TRY_FILES
    ]

    for path in test_paths:
        if not os.path.exists(path):
            print(f"Skipping {path}: file not found in repository")
            continue
        url = build_url(path)
        try:
            http_status = http_status_for(url)
            filename = path.split('/')[-1]
            if http_status < 400:
                line = f"- ✅ {filename} [HTTP {http_status}]: {url}\n\n"
            else:
                line = f"- ❌ {filename} [HTTP {http_status}]: {url}\n\n"
                success = False
        except URLError as exc:
            line = f"- ❌ {filename} [URL ERROR]: {url}\n\n```\n{exc}\n```"
            success = False
        comment += line

    if not success:
        comment += (
            "\n\n"
            "🚨 One or more Lab pages are returning an error. "
            "Please follow the link to see details of the issue."
        )

    create_or_update_comment(lab_name, comment)
    return success


def http_status_for(url):
    try:
        response = urlopen(url)
        return response.getcode()
    except HTTPError as e:
        return e.code


def build_url(content_path):
    return URL_TEMPLATE.format(
        repo=HEAD_REPO,
        branch_name=BRANCH_NAME,
        lab_content_path=content_path)


def main():
    path = sys.argv[1] if len(sys.argv) else "paths.txt"
    with open(path) as f:
        files = f.read().splitlines()

    success = True
    directories = []

    # Check each file to see if it is in a "Lab" directory
    for path in files:
        if path.startswith("communities/") and "/lab/" in path:
            lab_name = path.split("/")[1]
            if lab_name not in directories:
                print(f"Detected change to {lab_name} Lab in file: {path}")
                print(f"Posting link for {lab_name}...")
                directories.append(lab_name)
                result = post_lab_links(lab_name)
                success = success and result
        else:
            print(f"Ignoring changes to {path}: not in a lab directory")

    if not success:
        raise ValueError("One or more Lab pages returned an HTTP error.")


if __name__ == "__main__":
    main()
