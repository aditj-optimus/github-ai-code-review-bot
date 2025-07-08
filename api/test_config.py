import unittest
from unittest.mock import patch, MagicMock
import api.config as config
from azure.core.exceptions import HttpResponseError, ServiceRequestError

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.patcher_client = patch('api.config.client')
        self.mock_client = self.patcher_client.start()
        self.mock_secret = MagicMock()
        self.mock_secret.value = 'secret_value'
        self.mock_client.get_secret.return_value = self.mock_secret

    def tearDown(self):
        patch.stopall()

    def test_get_secret_success(self):
        value = config.get_secret('test-secret')
        self.assertEqual(value, 'secret_value')

    def test_get_secret_none_value(self):
        self.mock_secret.value = None
        with self.assertRaises(Exception):
            config.get_secret('test-secret')

    def test_get_secret_retry_and_fail(self):
        self.mock_client.get_secret.side_effect = HttpResponseError('fail')
        with self.assertRaises(Exception):
            config.get_secret('test-secret', max_retries=2, backoff_factor=0)

    def test_get_secret_retry_and_succeed(self):
        # Fail first, succeed second
        self.mock_client.get_secret.side_effect = [HttpResponseError('fail'), self.mock_secret]
        value = config.get_secret('test-secret', max_retries=2, backoff_factor=0)
        self.assertEqual(value, 'secret_value')

if __name__ == '__main__':
    unittest.main() 