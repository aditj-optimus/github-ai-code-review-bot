import os
import logging
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import HttpResponseError, ServiceRequestError
from time import sleep

# Project/App Metadata (for reference and future use, no secrets here)
APP_METADATA = {
    "github_app_name": "AI-Code-Review-Bot-main",
    "homepage_url": "https://ashy-flower-06b716f10.2.azurestaticapps.net",
    "app_id": "1484338",
    "client_id": "Iv23liX7VIsQHKdZtOa6",
    "webhook_url": "https://AI-Code-Review-Bot-main.azurestaticapps.net/api/webhook",
    "github_app_link": "https://github.com/apps/ai-code-review-bot-main",
    "azure_key_vault": "ai-review-vault-main",
    "ai_search_endpoint": "https://aicodereview-search.search.windows.net",
    "prompt_flow_endpoint": "https://aditjain-3239-hjvrz.eastus2.inference.ml.azure.com/score",
    "key_vault_url": os.getenv("KEY_VAULT_URL", "https://ai-review-vault-main.vault.azure.net/"),
    "installation_id": 73640100,
    "github_username": "aditj-optimus",
    "repo_name": "github-ai-code-review-bot",
    "code_fix_prompt_flow_endpoint": "https://code-fix-flow.eastus2.inference.ml.azure.com/score"
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch Key Vault URL from environment variable or APP_METADATA
VAULT_URL = os.getenv("KEY_VAULT_URL") or APP_METADATA["key_vault_url"]
if not VAULT_URL:
    logger.error("KEY_VAULT_URL environment variable is not set and no fallback available.")
    raise ValueError("KEY_VAULT_URL environment variable is required.")

# Use Managed Identity for authentication (DefaultAzureCredential)
credential = DefaultAzureCredential()
client = SecretClient(vault_url=VAULT_URL, credential=credential)

def get_secret(name: str, max_retries: int = 3, backoff_factor: float = 2.0) -> str:
    """
    Fetch a secret value from Azure Key Vault with retry logic.
    Args:
        name (str): Name of the secret in Key Vault.
        max_retries (int): Number of retries for transient errors.
        backoff_factor (float): Exponential backoff factor.
    Returns:
        str: Secret value.
    Raises:
        Exception: If secret cannot be retrieved after retries.
    """
    attempt = 0
    while attempt < max_retries:
        try:
            secret = client.get_secret(name)
            logger.info(f"Successfully fetched secret: {name}")
            value = secret.value
            if value is None:
                logger.error(f"Secret '{name}' found but value is None.")
                raise Exception(f"Secret '{name}' value is None.")
            return value
        except (HttpResponseError, ServiceRequestError) as e:
            logger.warning(f"Attempt {attempt+1} failed to fetch secret '{name}': {e}")
            sleep(backoff_factor ** attempt)
            attempt += 1
        except Exception as e:
            logger.error(f"Unexpected error fetching secret '{name}': {e}")
            raise
    logger.error(f"Failed to fetch secret '{name}' after {max_retries} attempts.")
    raise Exception(f"Failed to fetch secret '{name}' after {max_retries} attempts.")

# Example usage (uncomment to use):
# secret_value = get_secret("my-secret-name")
# print(secret_value)

# Security Note:
# - Ensure the managed identity has 'get' permission for secrets in the Key Vault access policies.
# - Never log or print secret values in production.
# - Rotate secrets regularly and use least privilege access.

# Reference:
# https://learn.microsoft.com/en-us/azure/key-vault/secrets/quick-create-python
# https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/keyvault/azure-keyvault-secrets

# CODE_FIX_PROMPT_FLOW_ENDPOINT and CODE_FIX_PROMPT_FLOW_API_KEY are now loaded from environment or Key Vault for code-fix integration.
CODE_FIX_PROMPT_FLOW_ENDPOINT = os.getenv("CODE_FIX_PROMPT_FLOW_ENDPOINT") or APP_METADATA.get("code_fix_prompt_flow_endpoint") or "https://code-fix-flow.eastus2.inference.ml.azure.com/score"
CODE_FIX_PROMPT_FLOW_API_KEY = get_secret("prompt-flow-api-key-2")
