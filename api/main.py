from api.config import get_secret, APP_METADATA
import hmac
import hashlib
import os
import json
import requests
import logging
from api.github_api import get_installation_token, fetch_pr_data, post_pr_comment

logger = logging.getLogger(__name__)

GITHUB_APP_ID = get_secret("github-app-id")
GITHUB_PRIVATE_KEY_PEM = get_secret("github-private-key-pem")
GITHUB_WEBHOOK_SECRET = get_secret("github-webhook-secret")
PROMPT_FLOW_API_KEY = get_secret("prompt-flow-api-key")
AI_SEARCH_ENDPOINT = get_secret("ai-search-endpoint")

def validate_signature(payload, header_signature, secret):
    """
    Validate the GitHub webhook signature using HMAC SHA256.
    """
    if not header_signature:
        logger.warning("Missing X-Hub-Signature-256 header.")
        return False
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
    expected = f"sha256={mac.hexdigest()}"
    return hmac.compare_digest(expected, header_signature)

def main(req):
    """
    Azure Function entry point for handling GitHub PR webhooks.
    """
    secret = get_secret("github-webhook-secret")
    payload = req.get_body()
    signature = req.headers.get("X-Hub-Signature-256")

    if not validate_signature(payload, signature, secret):
        logger.error("Invalid webhook signature.")
        return {"status": 401, "body": "Invalid signature"}

    data = json.loads(payload)

    # Only handle pull_request events for opened or synchronize
    if data.get("action") not in ["opened", "synchronize"]:
        return {"status": 200, "body": "Ignored event"}

    # Use metadata defaults if not present in payload
    repo = data["repository"].get("name") or APP_METADATA["repo_name"]
    owner = data["repository"].get("owner", {}).get("login") or APP_METADATA["github_username"]
    pr_number = data["pull_request"].get("number")
    installation_id = data["installation"].get("id") or APP_METADATA["installation_id"]

    app_id = get_secret("github-app-id")
    private_key = get_secret("github-private-key-pem")
    pf_api_key = get_secret("prompt-flow-api-key")
    pf_endpoint = os.getenv("PROMPT_FLOW_ENDPOINT") or APP_METADATA["prompt_flow_endpoint"]
    if not pf_endpoint:
        logger.error("PROMPT_FLOW_ENDPOINT environment variable is not set and no fallback available.")
        return {"status": 500, "body": "Prompt Flow endpoint not configured."}

    try:
        token = get_installation_token(app_id, private_key, installation_id)
        code_diff, commit_msg = fetch_pr_data(owner, repo, pr_number, token)
    except Exception as e:
        logger.error(f"GitHub API error: {e}")
        return {"status": 500, "body": "Failed to fetch PR data."}

    def detect_language_from_files(owner, repo, pr_number, token):
        """
        Detect programming language from PR file extensions.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.warning("Could not fetch PR files for language detection.")
            return "python"  # fallback
        files = response.json()
        extensions = [os.path.splitext(f['filename'])[1] for f in files]
        # Simple mapping, expand as needed
        if any(ext in ['.py'] for ext in extensions):
            return "python"
        if any(ext in ['.js', '.jsx'] for ext in extensions):
            return "javascript"
        if any(ext in ['.ts', '.tsx'] for ext in extensions):
            return "typescript"
        if any(ext in ['.java'] for ext in extensions):
            return "java"
        if any(ext in ['.cs'] for ext in extensions):
            return "csharp"
        if any(ext in ['.go'] for ext in extensions):
            return "go"
        if any(ext in ['.rb'] for ext in extensions):
            return "ruby"
        if any(ext in ['.php'] for ext in extensions):
            return "php"
        if any(ext in ['.cpp', '.cc', '.cxx', '.hpp', '.h'] for ext in extensions):
            return "cpp"
        if any(ext in ['.c'] for ext in extensions):
            return "c"
        if any(ext in ['.swift'] for ext in extensions):
            return "swift"
        if any(ext in ['.kt', '.kts'] for ext in extensions):
            return "kotlin"
        return "python"  # default fallback

    def get_project_name_from_guidelines(owner, repo, token):
        """
        Try to fetch and parse .guidelines.yml from the repo root. If not found or error, fallback to repo name.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/.guidelines.yml"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.raw"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            try:
                import yaml
                yml_content = response.text
                yml_data = yaml.safe_load(yml_content)
                # Try to get a project_name field, fallback to repo name if not present
                return yml_data.get("project_name", repo)
            except Exception as e:
                logger.warning(f"Failed to parse .guidelines.yml: {e}")
                return repo
        else:
            logger.info(".guidelines.yml not found, using repo name as project_name.")
            return repo

    language = detect_language_from_files(owner, repo, pr_number, token)
    project_name = get_project_name_from_guidelines(owner, repo, token)

    flow_input = {
        "commit_msg": commit_msg,
        "code_diff": code_diff,
        "project_name": project_name,
        "language": language
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {pf_api_key}"
    }

    try:
        pf_response = requests.post(pf_endpoint, headers=headers, json=flow_input)
        pf_response.raise_for_status()
        review_comment = pf_response.json().get("output", "No review output.")
    except Exception as e:
        logger.error(f"Prompt Flow call failed: {e}")
        return {"status": 500, "body": "Prompt Flow call failed."}

    try:
        status = post_pr_comment(owner, repo, pr_number, review_comment, token)
    except Exception as e:
        logger.error(f"Failed to post PR comment: {e}")
        return {"status": 500, "body": "Failed to post PR comment."}

    # Post follow-up comment with fix options
    try:
        fix_options_comment = (
            "\n---\n"
            "### 🛠️ Want to fix issues automatically?\n"
            "Comment `/apply-fix` to let the bot suggest a patch (no commit).\n"
            "Comment `/apply-and-commit` to let the bot apply and commit the fix to this branch.\n"
            "\n> Only users with write access can trigger these actions."
        )
        post_pr_comment(owner, repo, pr_number, fix_options_comment, token)
    except Exception as e:
        logger.warning(f"Failed to post fix options comment: {e}")

    # Listen for /apply-fix or /apply-and-commit commands
    from api.github_api import get_pr_comments, detect_apply_fix_command, generate_code_fixes_with_copilot, commit_code_changes
    comments = get_pr_comments(owner, repo, pr_number, token)
    # Optionally, fetch list of users with write access for approval (not implemented here)
    # approval_users = ...
    apply_fix = False
    apply_and_commit = False
    for comment in comments:
        body = comment.get('body', '').strip().lower()
        if '/apply-fix' in body:
            apply_fix = True
        if '/apply-and-commit' in body:
            apply_and_commit = True
    if apply_fix or apply_and_commit:
        try:
            # Use review_comment as context for the LLM/code-fix engine
            try:
                # Pass review_comment as an input to the code fix generator (Copilot/OpenAI)
                fixed_files = generate_code_fixes_with_copilot(
                    code_diff, review_comment, pf_api_key
                )
            except NotImplementedError:
                # For demo, show a dummy patch preview if not implemented
                dummy_patch = {'example.py': '# Example fix\nprint("Hello, fixed!")\n'}
                if apply_fix:
                    patch_preview = '\n'.join([
                        f"**{path}**\n```diff\n{dummy_patch[path]}\n```" for path in dummy_patch
                    ])
                    post_pr_comment(
                        owner, repo, pr_number,
                        f"### 🤖 Suggested Fixes (Preview)\n{patch_preview}\n\n*Copilot code fix generation is not implemented in this demo.*",
                        token
                    )
                if apply_and_commit:
                    post_pr_comment(
                        owner, repo, pr_number,
                        "Copilot code fix generation and commit is not implemented.",
                        token
                    )
                return {"status": 200, "body": "Fix feature not implemented."}
            if not fixed_files or not isinstance(fixed_files, dict):
                post_pr_comment(
                    owner, repo, pr_number,
                    "No fixable suggestions were found or fixes could not be generated based on the review and guidelines.",
                    token
                )
                return {"status": 200, "body": "No fixable suggestions."}
            if apply_fix:
                patch_preview = '\n'.join([
                    f"**{path}**\n```diff\n{fixed_files[path]}\n```" for path in fixed_files
                ])
                post_pr_comment(owner, repo, pr_number, f"### 🤖 Suggested Fixes (Preview)\n{patch_preview}", token)
            if apply_and_commit:
                try:
                    commit_msg = f"chore(bot): apply automated fixes for PR #{pr_number}"
                    branch = data["pull_request"]["head"]["ref"]
                    commit_code_changes(owner, repo, branch, fixed_files, commit_msg, token)
                    post_pr_comment(owner, repo, pr_number, "✅ Automated fixes have been committed to this branch.", token)
                except Exception as e:
                    logger.error(f"Failed to commit code fixes: {e}")
                    post_pr_comment(owner, repo, pr_number, f"Failed to commit code fixes: {e}", token)
                    return {"status": 500, "body": "Failed to commit code fixes."}
        except Exception as e:
            logger.error(f"Failed to generate code fixes: {e}")
            post_pr_comment(owner, repo, pr_number, f"Failed to generate code fixes: {e}", token)
            return {"status": 500, "body": "Failed to generate code fixes."}

    return {"status": status, "body": "Review posted."}

# Security Note:
# - Never log or print secret values.
# - Validate all incoming webhook signatures.
# - Handle all API errors and log failures for monitoring.
#
# Reference:
# https://docs.github.com/en/webhooks-and-events/webhooks/securing-your-webhooks
# https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python