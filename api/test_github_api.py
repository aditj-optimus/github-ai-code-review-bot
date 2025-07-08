import unittest
from unittest.mock import patch, MagicMock
import api.github_api as github_api

class TestGithubApi(unittest.TestCase):
    def setUp(self):
        self.patcher_get_secret = patch('api.config.get_secret', return_value='dummy')
        self.patcher_get_secret.start()
        self.patcher_requests_post = patch('requests.post')
        self.mock_post = self.patcher_requests_post.start()
        self.patcher_requests_get = patch('requests.get')
        self.mock_get = self.patcher_requests_get.start()

    def tearDown(self):
        patch.stopall()

    def test_generate_jwt(self):
        token = github_api.generate_jwt('appid', 'privatekey')
        self.assertIsInstance(token, str)

    def test_get_installation_token_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'token': 'abc'}
        self.mock_post.return_value = mock_response
        token = github_api.get_installation_token('appid', 'privatekey', 123)
        self.assertEqual(token, 'abc')

    def test_get_installation_token_failure(self):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'fail'
        self.mock_post.return_value = mock_response
        with self.assertRaises(Exception):
            github_api.get_installation_token('appid', 'privatekey', 123)

    def test_fetch_pr_data_success(self):
        pr_json = {'diff_url': 'url', 'title': 'msg'}
        mock_pr = MagicMock()
        mock_pr.status_code = 200
        mock_pr.json.return_value = pr_json
        mock_diff = MagicMock()
        mock_diff.status_code = 200
        mock_diff.text = 'diff'
        self.mock_get.side_effect = [mock_pr, mock_diff]
        diff, msg = github_api.fetch_pr_data('owner', 'repo', 1, 'token')
        self.assertEqual(diff, 'diff')
        self.assertEqual(msg, 'msg')

    def test_fetch_pr_data_failure(self):
        mock_pr = MagicMock()
        mock_pr.status_code = 400
        mock_pr.text = 'fail'
        self.mock_get.return_value = mock_pr
        with self.assertRaises(Exception):
            github_api.fetch_pr_data('owner', 'repo', 1, 'token')

    def test_post_pr_comment_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 201
        self.mock_post.return_value = mock_response
        status = github_api.post_pr_comment('owner', 'repo', 1, 'comment', 'token')
        self.assertEqual(status, 201)

    def test_post_pr_comment_failure(self):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'fail'
        self.mock_post.return_value = mock_response
        with self.assertRaises(Exception):
            github_api.post_pr_comment('owner', 'repo', 1, 'comment', 'token')

    def test_get_pr_comments_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'body': 'hi'}]
        self.mock_get.return_value = mock_response
        comments = github_api.get_pr_comments('owner', 'repo', 1, 'token')
        self.assertEqual(comments, [{'body': 'hi'}])

    def test_get_pr_comments_failure(self):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'fail'
        self.mock_get.return_value = mock_response
        with self.assertRaises(Exception):
            github_api.get_pr_comments('owner', 'repo', 1, 'token')

if __name__ == '__main__':
    unittest.main() 