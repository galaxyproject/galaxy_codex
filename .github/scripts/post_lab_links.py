"""Build URLs for each Lab page for Labs that have been changed in this PR.

Test each URL to see if it returns a 200 status code, and post the results
in a PR comment.
"""

import os
import requests
import sys
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

COMMENT_ID_STRING = "<!-- labs-links-comment -->"
URL_TEMPLATE = (
    "https://labs.usegalaxy.org.au"
    "/?content_root=https://github.com/{username}/galaxy_codex"
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
USERNAME = os.environ["GITHUB_ACTOR"]
BRANCH_NAME = os.environ["GITHUB_HEAD_REF"]
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}


def get_comment_id():
    """Fetches PR comments and finds one with the unique identifier."""
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    comments = response.json()

    for comment in comments:
        if COMMENT_ID_STRING in comment["body"]:
            return comment["id"]
    return None


def update_comment(comment_id, new_body):
    """Updates an existing comment by ID with new content."""
    url = f"https://api.github.com/repos/{REPO}/issues/comments/{comment_id}"
    response = requests.patch(url, headers=headers, json={"body": new_body})
    response.raise_for_status()
    print("Comment updated successfully.")


def create_comment(new_body):
    """Creates a new comment on the PR."""
    tagged_body = f"{new_body}\n\n{COMMENT_ID_STRING}"
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    response = requests.post(url, headers=headers, json={"body": tagged_body})
    response.raise_for_status()
    print("Comment created successfully.")


def create_or_update_comment(new_body):
    """Creates or updates a comment with the unique identifier."""
    comment_id = get_comment_id()
    if comment_id:
        update_comment(comment_id, new_body)
    else:
        create_comment(new_body)


def post_lab_links(name):
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
        url = build_url(USERNAME, BRANCH_NAME, path)
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


def build_url(username, branch_name, content_path):
    return URL_TEMPLATE.format(
        username=username,
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
        sys.exit(1)


if __name__ == "__main__":
    main()
