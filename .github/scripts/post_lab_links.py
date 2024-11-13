import os
import subprocess
import urllib

URL_TEMPLATE = (
    "https://labs.usegalaxy.org.au"
    "/?content_root=https://github.com/{username}/galaxy_codex"
    "/blob/{branch_name}/{lab_content_path}"
    "&cache=false"
)
# Environment variables from GitHub Actions
PR_NUMBER = os.getenv("PR_NUMBER")
USERNAME = os.getenv("GITHUB_ACTOR")
BRANCH_NAME = os.getenv("GITHUB_HEAD_REF")


def post_lab_links(name):
    success = True
    comment = f"### Preview changes to {name} Lab\n\n"
    test_paths = [
        f'communities/{name}/lab/base.yml',
        f'communities/{name}/lab/usegalaxy.eu.yml',
        f'communities/{name}/lab/usegalaxy.org.yml',
        f'communities/{name}/lab/usegalaxy.org.au.yml',
    ]

    for path in test_paths:
        url = build_url(USERNAME, BRANCH_NAME, path)
        http_status = http_status_for(url)
        filename = path.split('/')[-1]
        if http_status < 400:
            comment += f"- ✅ {filename} [{http_status}]: {url}\n\n"
        else:
            comment += f"- ❌ {filename} [{http_status}]: {url}\n\n"
            success = False

    if not success:
        comment += (
            "\n\n"
            "🚨 One or more Lab pages are returning an error. "
            "Please follow the link to see the issue."
        )

    # Post the comment using gh CLI
    subprocess.run([
        "gh",
        "pr",
        "comment",
        PR_NUMBER,
        "--body",
        comment,
    ], check=True)
    return success


def http_status_for(url):
    try:
        response = urllib.urlopen(url)
        return response.getcode()
    except urllib.error.HTTPError as e:
        return e.code


def build_url(username, branch_name, content_path):
    return URL_TEMPLATE.format(
        username=username,
        branch_name=branch_name,
        lab_content_path=content_path)


def main():
    with open("changed_files.txt") as f:
        files = f.read().splitlines()

    # Track directories that have already been seen
    directories = []

    # Check each file to see if it is in a "Lab" directory
    for path in files:
        if path.startswith("communities/") and "/lab/" in path:
            name = path.split("/")[1]
            if name not in directories:
                print(f"Posting link for {name}...")
                directories.append(name)
                post_lab_links(name)
        else:
            print(f"Ignoring changes to {path}: not in a lab directory")


if __name__ == "__main__":
    main()
