# CXM IAC Crawler

Multi-platform Infrastructure as Code crawler for scanning Terraform configurations and sending resource data to the CXM API.

## Features

- **Multi-Platform Support**: GitHub Actions and GitLab CI
- **Automatic Platform Detection**: Detects CI/CD environment and collects metadata automatically
- **Terraform Discovery**: Recursively finds `.terraform.lock.hcl` files
- **Resource Extraction**: Executes `terraform show -json` to extract infrastructure state
- **Sensitive Data Sanitization**: Automatically redacts sensitive values
- **Batch Processing**: Sends resources to CXM API in configurable batches with retry logic
- **Docker-Based**: Single Docker image works across all platforms

## Quick Start

### GitHub Actions

**Important:** You must checkout your repository before using this action.

```yaml
name: Scan Terraform Infrastructure
on:
  push:
    branches: [main]
  pull_request:

jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      # ⚠️ REQUIRED: Checkout repository first
      - name: Checkout code
        uses: actions/checkout@v4

      # Run the IAC crawler
      - name: Scan Terraform
        uses: ./src/cxm-crawlers/cxm_iac_crawler/integrations/github
        with:
          cxm-api-key: ${{ secrets.CXM_API_KEY }}
          cxm-api-endpoint: ${{ secrets.CXM_API_ENDPOINT }}
          verbose: 'true'
```

### GitLab CI

**Note:** GitLab CI automatically clones your repository, so no additional checkout step is needed.

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/koomo/cxm/main/src/cxm-crawlers/cxm_iac_crawler/integrations/gitlab/.gitlab-ci.yml'

cxm-terraform-scan:
  extends: .cxm_iac_scan
  variables:
    CXM_API_KEY: ${CXM_API_KEY}
    CXM_API_ENDPOINT: ${CXM_API_ENDPOINT}
    INPUT_VERBOSE: "true"
```

### Local Development / Docker

```bash
docker run -it --rm \
  -e CXM_API_KEY="your-api-key" \
  -e CXM_API_ENDPOINT="https://api.cxm.example.com/ci-endpoints/resources" \
  -e INPUT_VERBOSE="true" \
  -v $(pwd):/scan \
  ghcr.io/koomo/cxm-iac-crawler:latest
```

## Configuration

### GitHub Actions Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `cxm-api-key` | CXM API key for authentication | Yes | - |
| `cxm-api-endpoint` | CXM API endpoint URL | No | - |
| `tf-entrypoints` | Specific Terraform entrypoint path(s) to scan (comma-separated). If provided, lock file discovery is skipped. | No | `` |
| `repository-url` | Repository URL to include in API requests (defaults to current repository URL) | No | `${{ github.repositoryUrl }}` |
| `verbose` | Enable verbose logging | No | `false` |
| `dry-run` | Enable dry-run mode (parse data without posting to API) | No | `false` |
| `terraform-show-timeout` | Timeout in seconds for terraform show command | No | `300` |
| `sensitive-fields` | Comma-separated list of additional sensitive field patterns to redact | No | `` |
| `max-retries` | Maximum number of retry attempts for API calls | No | `3` |
| `timeout-seconds` | Timeout in seconds for API calls | No | `30` |

### GitLab CI / Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `CXM_API_KEY` | CXM API key for authentication | Yes | - |
| `CXM_API_ENDPOINT` | CXM API endpoint URL | No | - |
| `INPUT_REPOSITORY_URL` | Repository URL (auto-detected if not provided) | No | Auto-detected |
| `INPUT_SCAN_PATH` | Directory to scan | No | `.` |
| `INPUT_VERBOSE` | Enable verbose logging | No | `false` |
| `INPUT_DRY_RUN` | Enable dry-run mode (parse data without posting to API) | No | `false` |
| `TERRAFORM_SHOW_TIMEOUT` | Terraform show timeout (seconds) | No | `300` |
| `SENSITIVE_FIELDS` | Comma-separated list of additional sensitive field patterns to redact | No | `` |
| `CXM_MAX_RETRIES` | Maximum API retry attempts | No | `3` |
| `CXM_TIMEOUT_SECONDS` | API call timeout (seconds) | No | `30` |

## How It Works

1. **Platform Detection**: Automatically detects CI/CD environment (GitHub, GitLab)
2. **Discovery**: Recursively searches for `.terraform.lock.hcl` files
3. **Extraction**: Runs `terraform show -json` in each directory
4. **Processing**: Extracts and flattens resources from module hierarchy
5. **Sanitization**: Removes sensitive data using Terraform's `sensitive_values` metadata
6. **Metadata Collection**: Collects platform-specific metadata (workflow ID, actor, etc.)
7. **Batching**: Groups resources into batches of 1000
8. **Transmission**: Sends batches to CXM API with retry logic

## Security

- Sensitive data is automatically redacted based on Terraform's `sensitive_values`
- Default redacted fields: `public_key`
- Redacted values are replaced with `**SENSITIVE**` or `**REDACTED**`
- API credentials should be stored in CI/CD secrets
- Never commit `CXM_API_KEY` to version control

## Error Handling

- Individual directory failures are logged but don't stop the scan
- Failed API requests are retried with exponential backoff
- Fatal errors (e.g., invalid credentials) exit with non-zero status
- Detailed error messages in verbose mode

## Troubleshooting

### Resources Not Found

**Problem**: No resources are being sent.

**Solutions**:
- Ensure `.terraform.lock.hcl` files exist in your repository
- Check that Terraform state is initialized (`terraform init`)
- Run with `verbose: true` to see detailed logs

### API Authentication Errors

**Problem**: 401/403 errors from CXM API.

**Solutions**:
- Verify `CXM_API_KEY` is set correctly
- Check API key has not expired
- Ensure `CXM_API_ENDPOINT` is correct

### Terraform Show Timeouts

**Problem**: Terraform show commands timeout.

**Solutions**:
- Increase `TERRAFORM_SHOW_TIMEOUT` (default: 300s)
- Check for large Terraform states
- Ensure Terraform backend is accessible

### Platform Detection Issues

**Problem**: Platform detected as "generic" instead of GitHub/GitLab.

**Solutions**:
- **GitHub Actions**: Ensure you're running inside a GitHub Actions workflow
- **GitLab CI**: Ensure you're running inside a GitLab CI pipeline
- Check environment variables are set (`GITHUB_ACTIONS` or `GITLAB_CI`)
- Enable verbose logging to see detected environment
- "generic" platform is expected for local development

## License

Proprietary - Cloud ex Machina
