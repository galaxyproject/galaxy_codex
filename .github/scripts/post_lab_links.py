"""Build URLs for each Lab page for Labs that have been changed in this PR.

Test each URL to see if it returns a 200 status code, and post the results
in a PR comment.
"""

import os
from github import Github
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

COMMENT_ID_STRING = "<!-- labs-links-comment -->"
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
PR_NUMBER = os.environ["PR_NUMBER"]
BRANCH_NAME = os.environ["GITHUB_HEAD_REF"]
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO)
pull_request = repo.get_pull(int(PR_NUMBER))


def get_comment():
    """Fetches PR comments and scans for the COMMENT_ID_STRING."""
    for comment in pull_request.get_issue_comments():
        if COMMENT_ID_STRING in comment.body:
            return comment
    return None


def create_or_update_comment(new_body):
    """Creates or updates a comment with the given body in markdown format.

    Checks for an existing comment by looking for the COMMENT_ID_STRING
    in existing comments.
    """
    tagged_body = f"{new_body}\n\n{COMMENT_ID_STRING}"
    comment = get_comment()
    if comment:
        comment.edit(tagged_body)
    else:
        pull_request.create_issue_comment(tagged_body)


def post_lab_links(name):
    """Iterate through each YAML root file for the given lab name.
    For files that exist, build a URL for that Lab page, check the HTTP status
    code and post the URLs with pass/fail status as a comment on the PR.
    """
    success = True
    comment = f"### Preview changes to {name} Lab\n\n"
    test_paths = [
        f'communities/{name}/lab/{f}'
        for f in TRY_FILES
    ]

    for path in test_paths:
        if not os.path.exists(path):
            print(f"Skipping {path}: file not found in repository")
            continue
        url = build_url(REPO, BRANCH_NAME, path)
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

    create_or_update_comment(comment)
    return success


def http_status_for(url):
    try:
        response = urlopen(url)
        return response.getcode()
    except HTTPError as e:
        return e.code


def build_url(repo, branch_name, content_path):
    return URL_TEMPLATE.format(
        repo=repo,
        branch_name=branch_name,
        lab_content_path=content_path)


def main():
    with open("changed_files.txt") as f:
        files = f.read().splitlines()

    success = True
    directories = []

    # Check each file to see if it is in a "Lab" directory
    for path in files:
        if path.startswith("communities/") and "/lab/" in path:
            name = path.split("/")[1]
            if name not in directories:
                print(f"Posting link for {name}...")
                directories.append(name)
                result = post_lab_links(name)
                success = success and result
        else:
            print(f"Ignoring changes to {path}: not in a lab directory")

    if not success:
        raise ValueError("One or more Lab pages returned an HTTP error.")


if __name__ == "__main__":
    main()
