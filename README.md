# dependency tasks
Create tasks in Asana from pull requests in all repositories associated with a GitHub organization.

## Dependencies
- Python 3 (tested on 3.9)
- [requests](https://pypi.org/project/requests/)
- [asana](https://pypi.org/project/asana/)
- [PyGithub](https://pypi.org/project/PyGithub/)

## Usage

The following environment variables are required:
- ASANA_ACCESS_TOKEN - a token that allows access to the Asana API, see [docs](https://developers.asana.com/docs/oauth)
- GITHUB_ACCESS_TOKEN	- a token that allows access to the GitHub API, see [docs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- ORG_NAME - the name of the GitHub organization
- PROJECT_ID - the id of the Asana project in which to create tasks
- SECTION_ID - the id of the section in the Asana project under which to create tasks

This source code is intended to be run as a [container image in AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html).


## License
This repository is released under an MIT License.
