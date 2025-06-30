# 🤖 GitHub AI Code Review Bot

Automatically reviews GitHub pull requests using GPT-4o, Azure Prompt Flow, and project-specific coding guidelines.

---

## 🚀 Features

- ✅ Reviews PR diffs and commit messages
- ✅ Enforces style, security, and project-specific rules
- ✅ Supports multiple languages (Python, C#, JavaScript, etc.)
- ✅ Posts feedback as a GitHub App bot
- ✅ Serverless architecture using Azure Static Web Apps
- ✅ Fully automated CI/CD and secret management

---

## ⚙️ Prerequisites

- Azure Subscription
- GitHub Account
- Azure AI Studio access
- Azure AI Search resource
- Azure Static Web App (Function enabled)

---

## 🛠 Setup Guide

### 1. Create GitHub App

- Go to: https://github.com/settings/apps → **New GitHub App**
- Set permissions:
  - **Read**: Contents, Pull requests
  - **Write**: Pull request comments
- Enable `pull_request` webhook event
- Generate:
  - App ID
  - PEM private key
  - Webhook secret

### 2. Set Up Azure Resources

- Create:
  - Azure Static Web App (with Python Function backend)
  - Azure Key Vault:
    - `GITHUB_APP_ID`
    - `GITHUB_PRIVATE_KEY_PEM`
    - `GITHUB_WEBHOOK_SECRET`
    - `PROMPT_FLOW_API_KEY`
    - `AI_SEARCH_ENDPOINT`
  - Azure AI Search:
    - Upload guideline docs
    - Configure semantic search index
  - Azure AI Studio:
    - Upload and deploy Prompt Flow

### 3. Deploy Using GitHub Actions

- Push to `main` branch
- GitHub Actions will:
  - Install dependencies
  - Deploy backend
  - Optional: re-index guideline docs

### 4. Install GitHub App on Project Repos

- Navigate to your GitHub App page → **Install App**
- Select one or more repos (e.g., `billing-service`)

---

## 💬 Example Bot Review Comment
🤖 Automated Review by CodeReviewBot
🔍 Issues Detected:
❗ Commit message is too vague. Use <type>: <summary> format.

⚠️ Variable dataList should follow snake_case (C# standard).

⚠️ Avoid using eval() – it’s insecure.

✅ Guidelines Followed:
No secrets detected

Tests appear complete

Review follows C# standards for Billing-Service.


---

## 🧠 Tech Stack

- GPT-4o via Azure Prompt Flow
- Azure AI Search (Semantic Index)
- Azure Functions (Python)
- GitHub Apps & Webhooks
- Azure Key Vault
- GitHub Actions CI/CD

---

## 📘 License

MIT License (or organization-specific)

---

## 🙌 Credits

Built by Adit Jain using Microsoft Azure, OpenAI, and GitHub APIs.

