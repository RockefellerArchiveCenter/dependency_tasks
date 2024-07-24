from unittest.mock import patch

import boto3
from moto import mock_ssm

from src.create_dependency_tasks import (dependency_prs, get_config, main,
                                         subtask_data, task_data)


class MockUser(object):
    def __init__(self, login):
        self.login = login


class MockHead(object):
    def __init__(self, ref):
        self.ref = ref


class MockPR(object):

    def __init__(self, title, dependabot=False, dependency_update=True):
        self.title = title
        if dependabot:
            self.user = MockUser("dependabot")
            self.head = MockHead("dependabot_update")
        if dependency_update:
            self.user = MockUser("user")
            self.head = MockHead("dependency-updates")


class MockRepo(object):

    def __init__(self, name):
        self.name = name

    def get_pulls(*args, **kwargs):
        return [
            MockPR("Dependabot PR", True, False),
            MockPR("Non-Dependabot PR", False, True),
        ]


@mock_ssm
def test_config():
    ssm = boto3.client('ssm', region_name='us-east-1')
    path = "/dev/digitization_tasks"
    for name, value in [("foo", "bar"), ("baz", "buzz")]:
        ssm.put_parameter(
            Name=f"{path}/{name}",
            Value=value,
            Type="SecureString",
        )
    config = get_config(path)
    assert config == {'foo': 'bar', 'baz': 'buzz'}


def test_dependency_prs():
    repo = MockRepo
    output = dependency_prs(repo)
    assert len(output) == 2


def test_task_data():
    """Tests that tasks are structured as expected."""

    repo_name = "Test Repository"
    pr_name = "This is a pull request"
    project_id = 654321
    section_id = 123
    output = task_data(MockRepo(repo_name),
                       [MockPR(pr_name, True, False),
                        MockPR(pr_name, False, True)],
                       project_id, section_id)
    assert output == {
        "data":
        {
            "completed": False,
            "name": repo_name,
            "notes": f"{pr_name}\n{pr_name}",
            "custom_fields": {
                "1200689146072910": "1200689146072911"
            },
            "projects": [project_id],
            "memberships": [
                {
                    "project": project_id,
                    "section": section_id
                }
            ]
        }
    }


def test_subtask_data():
    subtask_name = "subtask"
    parent_gid = 12345678
    output = subtask_data(subtask_name, {"gid": parent_gid})
    assert output == {
        'data': {
            'completed': False,
            'name': subtask_name,
            'parent': parent_gid
        }
    }


@patch('src.create_dependency_tasks.get_config')
@patch('github.Github.get_organization')
@patch('src.create_dependency_tasks.AsanaClient.tasks')
@patch('src.create_dependency_tasks.dependency_prs')
def test_main(mock_dependency_prs, mock_asana_tasks,
              mock_github_organization, mock_get_config):
    org_name = "RockefellerArchiveCenter"
    project_id = 123456789
    section_id = 987654321
    task_gid = 1234
    github_access_token = "1234abcdefg"
    asana_access_token = "98765fedcba"
    mock_get_config.return_value = {
        'GITHUB_ORG_NAME': org_name,
        'ASANA_PROJECT_ID': project_id,
        'ASANA_SECTION_ID': section_id,
        'GITHUB_ACCESS_TOKEN': github_access_token,
        'ASANA_ACCESS_TOKEN': asana_access_token
    }
    pr_list = [MockPR("foo"), MockPR("bar")]
    repo_list = [MockRepo("tool"), MockRepo("app"), MockRepo("library")]
    mock_github_organization.return_value.get_repos.return_value = repo_list
    mock_asana_tasks.create_tasks.return_value = {"gid": task_gid}
    mock_dependency_prs.return_value = pr_list

    main()

    mock_get_config.assert_called_once()
    mock_get_config.assert_called_with('/dev/dependency_tasks')
    mock_github_organization.assert_called_once()
    assert mock_asana_tasks.create_task.call_count == len(repo_list)
    assert mock_asana_tasks.create_subtask_for_task.call_count == len(
        repo_list) * 2
