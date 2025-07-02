# github_api.py
# Authenticate GitHub App using JWT and post PR comment via GitHub API

import jwt
import time
import requests
import json
import logging
import os
from api.config import get_secret, APP_METADATA

GITHUB_API_URL = "https://api.github.com"

# Load secrets securely from Azure Key Vault (do not use hardcoded values)
GITHUB_APP_ID = get_secret("github-app-id")
GITHUB_PRIVATE_KEY_PEM = get_secret("github-private-key-pem")
GITHUB_WEBHOOK_SECRET = get_secret("github-webhook-secret")
PROMPT_FLOW_API_KEY = get_secret("prompt-flow-api-key")
AI_SEARCH_ENDPOINT = get_secret("ai-search-endpoint")
PROMPT_FLOW_ENDPOINT = os.getenv("PROMPT_FLOW_ENDPOINT") or APP_METADATA["prompt_flow_endpoint"]

logger = logging.getLogger(__name__)

def generate_jwt(app_id: str, private_key: str) -> str:
    """
    Generate a JWT for GitHub App authentication.
    """
    payload = {
        "iat": int(time.time()) - 60,  # issued at time
        "exp": int(time.time()) + 540,  # expires after 9 minutes (GitHub requires <10min)
        "iss": app_id
    }
    token = jwt.encode(payload, private_key, algorithm="RS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token

def get_installation_token(app_id=None, private_key_pem=None, installation_id=None):
    """
    Exchange JWT for a GitHub App installation access token.
    If any argument is None, fetch from secrets/APP_METADATA.
    """
    if app_id is None:
        app_id = get_secret("github-app-id")
    if private_key_pem is None:
        private_key_pem = get_secret("github-private-key-pem")
    if installation_id is None:
        installation_id = APP_METADATA.get("installation_id")
    if not installation_id:
        logger.error("Installation ID is required but not found.")
        raise Exception("Installation ID is required.")
    jwt_token = generate_jwt(app_id, private_key_pem)
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }
    url = f"{GITHUB_API_URL}/app/installations/{installation_id}/access_tokens"
    response = requests.post(url, headers=headers)
    if response.status_code != 201:
        logger.error(f"Failed to get installation token: {response.status_code} {response.text}")
        raise Exception("Failed to get installation token")
    return response.json()["token"]

def fetch_pr_data(owner, repo, pr_number, token):
    """
    Fetch PR diff and commit message from GitHub.
    """
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    pr = requests.get(url, headers=headers)
    if pr.status_code != 200:
        logger.error(f"Failed to fetch PR data: {pr.status_code} {pr.text}")
        raise Exception("Failed to fetch PR data")
    pr_json = pr.json()
    diff_url = pr_json["diff_url"]
    diff = requests.get(diff_url, headers=headers)
    if diff.status_code != 200:
        logger.error(f"Failed to fetch PR diff: {diff.status_code} {diff.text}")
        raise Exception("Failed to fetch PR diff")
    commit_msg = pr_json["title"]
    return diff.text, commit_msg

def post_pr_comment(owner, repo, pr_number, comment, token):
    """
    Post a comment to a pull request using the GitHub App installation token.
    """
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    data = {"body": comment}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code != 201:
        logger.error(f"Failed to post PR comment: {response.status_code} {response.text}")
        raise Exception("Failed to post PR comment")
    return response.status_code

# Security Note:
# - Never log or print secret values.
# - Handle all API errors and log failures for monitoring.
# - Use the installation token only for the required operations.
#
# Reference:
# https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app
# https://github.com/Azure/azure-sdk-for-python