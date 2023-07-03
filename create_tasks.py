#!/usr/bin/env python3

"""Create Asana tasks for every application which has open Dependabot PRs.

Requires encrypted GITHUB_ACCESS_TOKEN and ASANA_ACCESS_TOKEN environment variables to be set.
"""

from base64 import b64decode
from os import environ

import boto3
from asana import Client
from github import Github


def decrypt_env_variable(env_key):
    encrypted = environ.get(env_key)
    return boto3.client('kms').decrypt(
        CiphertextBlob=b64decode(encrypted),
        EncryptionContext={
            'LambdaFunctionName': environ['AWS_LAMBDA_FUNCTION_NAME']}
    )['Plaintext'].decode('utf-8')


ORG_NAME = decrypt_env_variable("ORG_NAME")
PROJECT_ID = decrypt_env_variable("PROJECT_ID")
SECTION_ID = decrypt_env_variable("SECTION_ID")


def main(event=None, context=None):
    task_count = 0
    gh_client = Github(decrypt_env_variable("GITHUB_ACCESS_TOKEN"))
    asana_client = Client.access_token(
        decrypt_env_variable("ASANA_ACCESS_TOKEN"))
    # opt-in to deprecation
    asana_client.headers = {
        'asana-enable': 'new_user_task_lists,new_project_templates'}
    repo_list = gh_client.get_organization(ORG_NAME).get_repos()
    for repo in repo_list:
        open_prs = dependency_prs(repo)
        if open_prs:
            task = asana_client.tasks.create_task(task_data(repo, open_prs))
            for subtask_name in [
                    "deploy development branch with updates",
                    "deploy production branch with updates"]:
                asana_client.tasks.create_task(
                    subtask_data(subtask_name, task))
            task_count += 1
    print(
        "{} {} created".format(
            task_count,
            "task" if task_count == 1 else "tasks"))
    return task_count


def dependency_prs(repo):
    """Returns all repository PRs for dependencies."""
    prs = repo.get_pulls(state="open")
    dependabot_prs = [u for u in prs if "dependabot" in u.user.login]
    dependency_update_prs = [
        u for u in prs if u.head.ref == "dependency-updates"]
    return list(set(dependabot_prs + dependency_update_prs))


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
        "name": repo.name,
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
