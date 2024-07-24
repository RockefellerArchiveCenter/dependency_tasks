#!/usr/bin/env python3

"""Create Asana tasks for every application which has open Dependabot PRs.

Requires encrypted GITHUB_ACCESS_TOKEN and ASANA_ACCESS_TOKEN environment variables to be set.
"""

import traceback
from os import environ

import asana
import boto3
from github import Auth, Github

# PARAMS
# ORG_NAME = decrypt_env_variable("ORG_NAME")
# PROJECT_ID = decrypt_env_variable("PROJECT_ID")
# SECTION_ID = decrypt_env_variable("SECTION_ID")
# GITHUB_ACCESS_TOKEN
# ASANA_ACCESS_TOKEN

# Env varaibles
# ENV
# APP_CONFIG_PATH


def get_config(ssm_parameter_path):
    """Fetch config values from Parameter Store.

    Args:
        ssm_parameter_path (str): Path to parameters

    Returns:
        configuration (dict): all parameters found at the supplied path.
    """
    configuration = {}
    ssm_client = boto3.client(
        'ssm',
        region_name=environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
    try:
        param_details = ssm_client.get_parameters_by_path(
            Path=ssm_parameter_path,
            Recursive=False,
            WithDecryption=True)

        for param in param_details.get('Parameters', []):
            param_path_array = param.get('Name').split("/")
            section_position = len(param_path_array) - 1
            section_name = param_path_array[section_position]
            configuration[section_name] = param.get('Value')

    except BaseException:
        print("Encountered an error loading config from SSM.")
        traceback.print_exc()
    finally:
        return configuration


class AsanaClient(object):
    def __init__(self, access_token):
        asana_config = asana.Configuration()
        asana_config.access_token = access_token
        self.client = asana.ApiClient(asana_config)

    @property
    def tasks(self):
        return asana.TasksApi(self.client)


def main(event=None, context=None):
    task_count = 0
    full_config_path = f"/{environ.get('ENV')}/{environ.get('APP_CONFIG_PATH')}"
    config = get_config(full_config_path)
    auth = Auth.Token(config.get("GITHUB_ACCESS_TOKEN"))
    gh_client = Github(auth=auth)
    asana_client = AsanaClient(config.get("ASANA_ACCESS_TOKEN"))
    repo_list = gh_client.get_organization(config.get("ORG_NAME")).get_repos()
    for repo in repo_list:
        open_prs = dependency_prs(repo)
        if open_prs:
            task = asana_client.tasks.create_task(
                task_data(repo, open_prs, config.get("PROJECT_ID"), config.get("SECTION_ID")), {})
            for subtask_name in [
                    "deploy development branch with updates",
                    "deploy production branch with updates"]:
                asana_client.tasks.create_subtask_for_task(
                    subtask_data(subtask_name, task), {})
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


def task_data(repo, pull_requests, project_id, section_id):
    """Formats initial task data."""
    return {
        "data": {
            "completed": False,
            "custom_fields": {
                "1200689146072910": "1200689146072911"
            },
            "name": repo.name,
            "notes": "\n".join([pr.title for pr in pull_requests]),
            "projects": [project_id],
            "memberships": [
                {
                    "project": project_id,
                    "section": section_id
                }
            ]
        }
    }


def subtask_data(subtask_name, parent):
    """Formats subtask data."""
    return {
        "data": {
            "completed": False,
            "name": subtask_name,
            "parent": parent["gid"]
        }
    }


if __name__ == "__main__":
    main()
