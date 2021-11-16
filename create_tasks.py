#!/usr/bin/env python3

"""Create Asana tasks for every application which has open Dependabot PRs.

Requires GITHUB_ACCESS_TOKEN and ASANA_ACCESS_TOKEN environment variables to be set.
"""

from os import environ
import requests

from asana import Client
from github import Github


ORG_NAME = environ.get("ORG_NAME")
PROJECT_ID = environ.get("PROJECT_ID")
SECTION_ID = environ.get("SECTION_ID")

def main(event=None, context=None):
    task_count = 0
    gh_client = Github(environ.get("GITHUB_ACCESS_TOKEN"))
    asana_client = Client.access_token(environ.get("ASANA_ACCESS_TOKEN"))
    asana_client.headers = {'asana-enable': 'new_user_task_lists'} # opt-in to deprecation
    repo_list = gh_client.get_organization(ORG_NAME).get_repos()
    for repo in repo_list:
        open_prs = dependabot_prs(repo)
        if open_prs:
            task = asana_client.tasks.create_task(task_data(repo, open_prs))
            for subtask_name in [
                    "check in updates to development branch",
                    "deploy development branch with updates",
                    "deploy production branch with updates"]:
                asana_client.tasks.create_task(subtask_data(subtask_name, task))
            task_count += 1
    print("{} {} created".format(task_count, "task" if task_count == 1 else "tasks"))
    return task_count

def dependabot_prs(repo):
    """Returns all repository PRs created by Dependabot."""
    prs = repo.get_pulls(state="open")
    return [u for u in prs if "dependabot" in u.user.login]

def has_security_pr(pull_requests):
    """Determines if one of the open Dependabot PRs is a security patch."""
    return bool([pr for pr in pull_requests if "Security" in pr.title])

def task_data(repo, pull_requests):
    """Formats initial task data."""
    data = {
        "completed": False,
        "custom_fields": {
          "1200689146072910": "1200689146072911"
        },
        "name": "{} ({} {})".format(repo.name, len(pull_requests), "update" if len(pull_requests) == 1 else "updates"),
        "notes": "\n".join([pr.title for pr in pull_requests]),
        "projects": [PROJECT_ID],
        "memberships": [
            {
                "project": PROJECT_ID,
                "section": SECTION_ID
            }
        ]
    }
    if has_security_pr(pull_requests):
        data["tags"] = ["1200696779362560"]
    return data

def subtask_data(subtask_name, parent):
    """Formats subtask data."""
    return {
        "completed": False,
        "name": subtask_name,
        "parent": parent["gid"]
    }

if __name__ == "__main__":
    main()
