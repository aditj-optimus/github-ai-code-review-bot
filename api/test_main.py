import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import types

# Import the main function from main.py
import api.main as main_module

class TestMainFunction(unittest.TestCase):
    def setUp(self):
        # Patch get_secret to return dummy values
        self.get_secret_patcher = patch('api.config.get_secret', side_effect=lambda k: 'dummy_secret')
        self.get_secret = self.get_secret_patcher.start()
        # Patch external functions
        self.token_patcher = patch('api.github_api.get_installation_token', return_value='dummy_token')
        self.fetch_pr_data_patcher = patch('api.github_api.fetch_pr_data', return_value=('diff', 'commit msg'))
        self.post_pr_comment_patcher = patch('api.github_api.post_pr_comment', return_value=201)
        self.get_pr_comments_patcher = patch('api.github_api.get_pr_comments', return_value=[])
        self.generate_code_fixes_patcher = patch('api.github_api.generate_code_fixes_with_copilot', return_value={})
        self.token_patcher.start()
        self.fetch_pr_data_patcher.start()
        self.post_pr_comment_patcher.start()
        self.get_pr_comments_patcher.start()
        self.generate_code_fixes_patcher.start()
        # Patch requests.post for Prompt Flow
        self.requests_post_patcher = patch('requests.post')
        self.mock_requests_post = self.requests_post_patcher.start()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"output": "Review comment"}
        self.mock_requests_post.return_value = mock_response
        # Patch requests.get for language detection
        self.requests_get_patcher = patch('requests.get')
        self.mock_requests_get = self.requests_get_patcher.start()
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = [{"filename": "test.py"}]
        self.mock_requests_get.return_value = mock_get_response

    def tearDown(self):
        patch.stopall()

    def make_req(self, body, headers=None):
        # Simulate Azure Functions HttpRequest
        req = MagicMock()
        req.get_body.return_value = body
        req.headers = headers or {}
        return req

    def test_valid_signature_and_event(self):
        # Patch validate_signature to always return True
        with patch.object(main_module, 'validate_signature', return_value=True):
            payload = json.dumps({
                "action": "opened",
                "repository": {"name": "repo", "owner": {"login": "owner"}},
                "pull_request": {"number": 1},
                "installation": {"id": 123}
            }).encode()
            req = self.make_req(payload, {"X-Hub-Signature-256": "sig"})
            result = main_module.main(req)
            self.assertEqual(result["status"], 200)
            self.assertIn("body", result)

    def test_invalid_signature(self):
        with patch.object(main_module, 'validate_signature', return_value=False):
            req = self.make_req(b'{}', {"X-Hub-Signature-256": "sig"})
            result = main_module.main(req)
            self.assertEqual(result["status"], 401)

    def test_ignored_event(self):
        with patch.object(main_module, 'validate_signature', return_value=True):
            payload = json.dumps({
                "action": "closed",
                "repository": {"name": "repo", "owner": {"login": "owner"}},
                "pull_request": {"number": 1},
                "installation": {"id": 123}
            }).encode()
            req = self.make_req(payload, {"X-Hub-Signature-256": "sig"})
            result = main_module.main(req)
            self.assertEqual(result["status"], 200)
            self.assertEqual(result["body"], "Ignored event")

    def test_prompt_flow_failure(self):
        # Simulate Prompt Flow API failure
        with patch.object(main_module, 'validate_signature', return_value=True):
            self.mock_requests_post.return_value.raise_for_status.side_effect = Exception("fail")
            payload = json.dumps({
                "action": "opened",
                "repository": {"name": "repo", "owner": {"login": "owner"}},
                "pull_request": {"number": 1},
                "installation": {"id": 123}
            }).encode()
            req = self.make_req(payload, {"X-Hub-Signature-256": "sig"})
            result = main_module.main(req)
            self.assertEqual(result["status"], 500)
            self.assertIn("Prompt Flow call failed", result["body"])

if __name__ == "__main__":
    unittest.main() 