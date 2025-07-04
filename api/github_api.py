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

def get_pr_comments(owner, repo, pr_number, token):
    """
    Fetch all comments for a pull request.
    """
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to fetch PR comments: {response.status_code} {response.text}")
        raise Exception("Failed to fetch PR comments")
    return response.json()

def detect_apply_fix_command(comments, approval_users=None):
    """
    Detect if any comment contains '/apply-fix' or is an approval from a user with write access.
    Optionally, pass a list of usernames with write access as approval_users.
    Returns True if found, else False.
    """
    for comment in comments:
        body = comment.get('body', '').strip().lower()
        user = comment.get('user', {}).get('login', '')
        if '/apply-fix' in body:
            return True
        if approval_users and user in approval_users and ('approved' in body or '+1' in body):
            return True
    return False

# Placeholder for Copilot integration (or Azure OpenAI with Copilot-like prompt)
def generate_code_fixes_with_copilot(diff, review_comments, prompt_flow_api_key=None):
    """
    Call the deployed Prompt Flow endpoint to generate code fixes based on the diff and review comments.
    Returns a dict mapping filenames to fixed code content.
    """
    from api.config import CODE_FIX_PROMPT_FLOW_ENDPOINT, CODE_FIX_PROMPT_FLOW_API_KEY
    endpoint = CODE_FIX_PROMPT_FLOW_ENDPOINT
    api_key = CODE_FIX_PROMPT_FLOW_API_KEY
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "code_diff": diff,
        "review_suggestions": review_comments
    }
    response = requests.post(endpoint, headers=headers, json=payload)
    if response.status_code != 200:
        logger.error(f"Code fix Prompt Flow failed: {response.status_code} {response.text}")
        raise Exception(f"Code fix Prompt Flow failed: {response.status_code} {response.text}")
    result = response.json()
    # Accept both {"fixed_files": {...}} and direct file dicts
    if "fixed_files" in result and isinstance(result["fixed_files"], dict):
        fixed_files = result["fixed_files"]
    elif isinstance(result, dict):
        fixed_files = result
    else:
        logger.error(f"Invalid code fix response: {result}")
        return {}
    return fixed_files

def commit_code_changes(owner, repo, branch, files, commit_message, token):
    """
    Commit code changes to the specified branch using the GitHub API.
    files: dict mapping file paths to new content (str)
    """
    # 1. Get the latest commit SHA of the branch
    ref_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/refs/heads/{branch}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    ref_resp = requests.get(ref_url, headers=headers)
    if ref_resp.status_code != 200:
        logger.error(f"Failed to get branch ref: {ref_resp.status_code} {ref_resp.text}")
        raise Exception("Failed to get branch ref")
    latest_commit_sha = ref_resp.json()['object']['sha']

    # 2. Get the tree SHA
    commit_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/commits/{latest_commit_sha}"
    commit_resp = requests.get(commit_url, headers=headers)
    if commit_resp.status_code != 200:
        logger.error(f"Failed to get commit: {commit_resp.status_code} {commit_resp.text}")
        raise Exception("Failed to get commit")
    tree_sha = commit_resp.json()['tree']['sha']

    # 3. Create blobs for each file
    blob_shas = {}
    for path, content in files.items():
        blob_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/blobs"
        blob_data = {"content": content, "encoding": "utf-8"}
        blob_resp = requests.post(blob_url, headers=headers, data=json.dumps(blob_data))
        if blob_resp.status_code != 201:
            logger.error(f"Failed to create blob for {path}: {blob_resp.status_code} {blob_resp.text}")
            raise Exception(f"Failed to create blob for {path}")
        blob_shas[path] = blob_resp.json()['sha']

    # 4. Create a new tree
    tree_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees"
    tree_data = {
        "base_tree": tree_sha,
        "tree": [
            {"path": path, "mode": "100644", "type": "blob", "sha": sha}
            for path, sha in blob_shas.items()
        ]
    }
    tree_resp = requests.post(tree_url, headers=headers, data=json.dumps(tree_data))
    if tree_resp.status_code != 201:
        logger.error(f"Failed to create tree: {tree_resp.status_code} {tree_resp.text}")
        raise Exception("Failed to create tree")
    new_tree_sha = tree_resp.json()['sha']

    # 5. Create a new commit
    commit_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/commits"
    commit_data = {
        "message": commit_message,
        "tree": new_tree_sha,
        "parents": [latest_commit_sha]
    }
    commit_resp = requests.post(commit_url, headers=headers, data=json.dumps(commit_data))
    if commit_resp.status_code != 201:
        logger.error(f"Failed to create commit: {commit_resp.status_code} {commit_resp.text}")
        raise Exception("Failed to create commit")
    new_commit_sha = commit_resp.json()['sha']

    # 6. Update the branch reference
    update_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/refs/heads/{branch}"
    update_data = {"sha": new_commit_sha}
    update_resp = requests.patch(update_url, headers=headers, data=json.dumps(update_data))
    if update_resp.status_code not in (200, 201):
        logger.error(f"Failed to update branch ref: {update_resp.status_code} {update_resp.text}")
        raise Exception("Failed to update branch ref")
    return new_commit_sha

# Security Note:
# - Never log or print secret values.
# - Handle all API errors and log failures for monitoring.
# - Use the installation token only for the required operations.
#
# Reference:
# https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app
# https://github.com/Azure/azure-sdk-for-python