# azure_provider.py
import base64
import requests


class AzureDevOpsProvider:
    def __init__(self, organization: str, project: str, repository: str, pat: str):
        self.organization = organization
        self.project = project
        self.repository = repository

        # encode PAT
        token = f":{pat}".encode("utf-8")
        self.auth_header = base64.b64encode(token).decode("utf-8")

        self.base_url = (
            f"https://dev.azure.com/{organization}/{project}"
            f"/_apis/git/repositories/{repository}"
        )

    def create_pr(self, source: str, target: str, title: str, description: str = ""):
        url = f"{self.base_url}/pullrequests?api-version=7.1-preview.1"

        payload = {
            "sourceRefName": f"refs/heads/{source}",
            "targetRefName": f"refs/heads/{target}",
            "title": title,
            "description": description,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.auth_header}",
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Azure PR creation failed {response.status_code}: {response.text}"
            )

        return response.json()
