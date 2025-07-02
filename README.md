# 🤖 GitHub AI Code Review Bot

Automatically reviews GitHub pull requests using GPT-4o, Azure Prompt Flow, and project-specific coding guidelines.

---

## 🚀 Features
- Reviews PR diffs and commit messages
- Enforces style, security, and project-specific rules
- Supports multiple languages (Python, C#, JavaScript, etc.)
- Posts feedback as a GitHub App bot
- Serverless architecture using Azure Static Web Apps
- Fully automated CI/CD and secret management

## 🧠 Tech Stack
- GPT-4o via Azure Prompt Flow
- Azure AI Search (Semantic Index)
- Azure Functions (Python)
- GitHub Apps & Webhooks
- Azure Key Vault
- GitHub Actions CI/CD

## 📘 License
MIT License (or organization-specific)

## 🙌 Credits
Built by Adit Jain using Microsoft Azure, OpenAI, and GitHub APIs.

---

## Table of Contents
1. [Objective](#objective)
2. [Prerequisites](#prerequisites)
3. [Setup Guide](#setup-guide)
4. [Example Bot Review Comment](#example-bot-review-comment)
5. [Architecture Overview](#architecture-overview)
6. [Folder Structure](#folder-structure)
7. [Prompt Flow Inputs & Template](#prompt-flow-inputs--template)
8. [Secret Storage](#secret-storage-azure-key-vault)
9. [GitHub Workflow](#github-workflow)
10. [Deployment Notes](#deployment-notes)
11. [Per-Repo Guidelines](#guidelinesyml-per-repo-configuration)

---

## Objective
Automatically review code commits and pull requests in GitHub using an LLM (GPT-4o).
- Follows organization guidelines (per project/language)
- Detects style violations, vague commit messages, insecure code, or anti-patterns
- Posts actionable feedback directly to the GitHub PR as a bot

## Prerequisites
- Azure Subscription
- GitHub Account
- Azure AI Studio access
- Azure AI Search resource
- Azure Static Web App (Function enabled)

## Setup Guide
### 1. Create GitHub App
- Go to: https://github.com/settings/apps → New GitHub App
- Set permissions:
  - Read: Contents, Pull requests
  - Write: Pull request comments
- Enable pull_request webhook event
- Generate:
  - App ID
  - PEM private key
  - Webhook secret

### 2. Set Up Azure Resources
- Create:
  - Azure Static Web App (with Python Function backend)
  - Azure Key Vault:
    - GITHUB_APP_ID
    - GITHUB_PRIVATE_KEY_PEM
    - GITHUB_WEBHOOK_SECRET
    - PROMPT_FLOW_API_KEY
    - AI_SEARCH_ENDPOINT
  - Azure AI Search:
    - Upload guideline docs
    - Configure semantic search index
  - Azure AI Studio:
    - Upload and deploy Prompt Flow

### 3. Deploy Using GitHub Actions
- Push to main branch
- GitHub Actions will:
  - Install dependencies
  - Deploy backend
  - Optional: re-index guideline docs

### 4. Install GitHub App on Project Repos
- Navigate to your GitHub App page → Install App
- Select one or more repos (e.g., billing-service)

---

## Example Bot Review Comment
```markdown
🤖 Automated Review by CodeReviewBot
🔍 Issues Detected:
❗ Commit message is too vague. Use <type>: <description> format.
⚠️ Variable dataList should follow snake_case (C# standard).
⚠️ Avoid using eval() – it’s insecure.

✅ Guidelines Followed: No secrets detected
Tests appear complete
Review follows C# standards for Billing-Service.
```

---

## Architecture Overview
```mermaid
graph TD;
    A[GitHub Pull Request] --> B[GitHub Webhook Event (pull_request)];
    B --> C[Azure Static Web App Function API];
    C --> D[Azure Prompt Flow];
    D --> E[Azure Function: Post PR Comment]
    C -->|Validates webhook, fetches diff, detects language, reads .guidelines.yml| D
    D -->|Retrieves guidelines, generates review| E
```

---

## Folder Structure
```text
github-ai-review-bot/
├── api/
│   ├── main.py                 # Azure Function for webhook
│   ├── github_api.py           # Fetch PR data, post comments
│   └── config.py               # Read secrets from Azure Key Vault
│
├── prompt_flow/
│   ├── flow.dag.yaml           # Prompt Flow DAG
│   ├── prompt.jinja            # LLM prompt template
│   └── schema.json             # I/O schema
│
├── guidelines_index/
│   ├── python_guidelines.md
│   ├── js_commit_rules.md
│   └── billing_project_rules.pdf
│
├── .github/
│   └── workflows/deploy.yml    # GitHub Actions CI/CD workflow
│
├── .env
├── requirements.txt
└── README.md
```

---

## Prompt Flow Inputs & Template
### Inputs
| Input Field   | Source         | Description                       |
|--------------|----------------|-----------------------------------|
| commit_msg    | GitHub PR      | PR's latest commit message        |
| code_diff     | GitHub API     | Changed lines/files               |
| project_name  | Config/.yml    | Optional hardcoded or inferred    |
| language      | File detection | Python, JS, C#, etc.              |
| retrieved_docs| AI Search      | Guidelines for language/project   |

### Prompt Template (prompt.jinja)
```jinja
system:
You are a senior AI software reviewer. You review pull requests for style, clarity, and security based on company guidelines. Be helpful, constructive, and kind. You may first reason through the review silently, then respond in the structured format.

user:
A developer submitted the following pull request.

Project: {{ project_name }}
Language: {{ language }}

---
**Commit Message**:
{{ commit_msg }}

**Code Changes**:
{{ code_diff }}

**Relevant Guidelines**:
{{ retrieved_docs }}
---

Instructions:
- Follow these steps:
  1. Validate the commit message format
  2. Review the code changes for style, clarity, security, or anti-patterns
  3. Refer to the guidelines while suggesting improvements
- Your feedback must:
  - Be formatted as Markdown
  - Include ✅ Good practices
  - Include ❗ Problems with fixes
  - Include 💡 Suggestions
  - End with a checklist

Tone: Friendly, actionable, concise, and encouraging.
```

---

## Secret Storage (Azure Key Vault)
| Key Name               | Usage                                 |
|------------------------|---------------------------------------|
| github-app-id          | Identify GitHub App                   |
| github-private-key-pem | Sign JWT to get installation token    |
| github-webhook-secret  | Verify webhook authenticity           |
| prompt-flow-api-key    | Authenticate Prompt Flow calls        |
| ai-search-endpoint     | Access guideline index                |

---

## GitHub Workflow
1. Developer opens or updates a PR
2. GitHub sends pull_request webhook to Azure Static Web App’s Function API
3. Function:
    - Validates webhook
    - Extracts repo, commit SHA, PR number
    - Authenticates with GitHub API using JWT
    - Fetches code diff and commit message
    - Detects project or reads from .guidelines.yml
    - Sends all inputs to Prompt Flow
4. Prompt Flow:
    - Retrieves relevant guidelines from Azure AI Search
    - Generates code review using GPT-4o
5. Function posts formatted feedback as a comment using GitHub App bot

---

## Deployment Notes
| Task                | Tool                                 |
|---------------------|--------------------------------------|
| Deploy backend API  | Azure Static Web Apps (with Functions)|
| Deploy Prompt Flow  | Azure AI Studio                      |
| Index guidelines    | Azure AI Search (Blob Indexer/SDK)   |
| Secure all secrets  | Azure Key Vault                      |
| Automate CI/CD      | GitHub Actions                       |

---

## Final Benefits
- Project- and language-aware reviews
- Lightweight, serverless backend (Static Web App + Function)
- No manual configuration per repo
- Fast visual prompt iteration with Prompt Flow
- Simple, secure secret management with Key Vault
- CI/CD streamlined using GitHub Actions

---

## .guidelines.yml (Per-Repo Configuration)

If you want to customize code review rules or metadata for a specific repository, add a `.guidelines.yml` file to the root of that repository. The bot will fetch and parse this file to determine the `project_name` and (optionally) other review settings.

**Example `.guidelines.yml`:**
```yaml
project_name: billing-service
review_rules:
  - Ensure all SQL queries use parameterization
  - Enforce snake_case for Python variables
  - Require docstrings for all public functions
  - Disallow use of eval()
  - Check for logging of sensitive data
```

- `project_name`: **(Required)** Used to identify the project in review comments and for guideline retrieval.
- `review_rules`: **(Optional)** List of custom rules or reminders for the reviewer LLM. You can add any fields your Prompt Flow or bot logic supports.

> **Fallback behavior:**
> If `.guidelines.yml` is missing or cannot be parsed, the bot defaults to using the repository name as the project name and logs an informational message. This ensures the bot always works, even if the file is missing.

---

#### ⚙️ How `.guidelines.yml` Integration Works

1. **Fetch:** The bot tries to fetch `.guidelines.yml` from the repo root using the GitHub API.
2. **Parse:**
    - If found, it parses the file for `project_name` and any other fields (e.g., `review_rules`).
    - If not found, it logs `.guidelines.yml not found, using repo name as project_name.` and uses the repo name.
3. **Fallback:**
    - If the file is missing or invalid, the bot continues using the repo name for guideline retrieval and review context.

> This approach guarantees robust, zero-config operation for all repositories, while allowing advanced customization when needed.
