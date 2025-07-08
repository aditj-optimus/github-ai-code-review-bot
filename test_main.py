import json
import hmac
import hashlib
from api import main

class MockRequest:
    def __init__(self, body, headers):
        self._body = body
        self.headers = headers
    def get_body(self):
        return self._body

# Example payload (customize as needed)
payload = {
    "action": "opened",
    "repository": {
        "name": "github-ai-code-review-bot",
        "owner": {"login": "aditj-optimus"}
    },
    "pull_request": {"number": 1},
    "installation": {"id": 73640100}
}
body = json.dumps(payload).encode("utf-8")

# Simulate a valid signature (replace with your actual secret for real test)
secret = "b7b7e579d0d3ed3e2522166dc3fadb0f7cba4f04b8397cadb608ce4a063ccb13"
mac = hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256)
signature = f"sha256={mac.hexdigest()}"

req = MockRequest(body, {"X-Hub-Signature-256": signature})

# Test code-fix Prompt Flow integration (mocked example)
def test_code_fix_flow():
    from api.github_api import generate_code_fixes_with_copilot
    code_diff = "--- a/main.py\n+++ b/main.py\n@@ def add(a, b):\n- return a + b\n+ return a + b + 1"
    review_suggestions = "The function adds 1 unnecessarily. Just return a + b."
    try:
        fixed_files = generate_code_fixes_with_copilot(code_diff, review_suggestions)
        print("Code Fix Flow Output:", fixed_files)
        assert isinstance(fixed_files, dict)
        assert "main.py" in fixed_files
        assert "return a + b" in fixed_files["main.py"]
        print("Code-fix Prompt Flow integration test passed.")
    except Exception as e:
        print("Code-fix Prompt Flow integration test failed:", e)

def test_review_prompt_flow():
    """Test the review Prompt Flow endpoint and secret."""
    import requests
    from api.config import APP_METADATA, get_secret
    pf_endpoint = APP_METADATA["prompt_flow_endpoint"]
    pf_api_key = get_secret("prompt-flow-api-key")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {pf_api_key}"
    }
    flow_input = {
        "commit_msg": "Fix: remove hardcoded API key from user service",
        "code_diff": "diff --git a/services/user.py b/services/user.py\nindex e69de29..a1b2c3d 100644\n--- a/services/user.py\n+++ b/services/user.py\n@@ def get_user():\n-    api_key = '1234567890abcdef'\n+    api_key = os.environ.get(\"API_KEY\")",
        "project_name": "Billing-Service",
        "language": "Python"
    }
    try:
        resp = requests.post(pf_endpoint, headers=headers, json=flow_input)
        print("Review Prompt Flow status:", resp.status_code)
        print("Review Prompt Flow output:", resp.json())
        assert resp.status_code == 200
        print("Review Prompt Flow integration test passed.")
    except Exception as e:
        print("Review Prompt Flow integration test failed:", e)

if __name__ == "__main__":
    result = main.main(req)
    print(result)
    test_code_fix_flow()
    test_review_prompt_flow()
