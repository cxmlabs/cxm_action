# GitHub Actions Integration

CXM IAC Crawler for GitHub Actions workflows.

## Usage

**Important:** You must checkout your repository before using this action.

### Basic Example

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
        uses: ./path/to/cxm_iac_crawler/integrations/github
        with:
          cxm-api-key: ${{ secrets.CXM_API_KEY }}
          cxm-api-endpoint: ${{ secrets.CXM_API_ENDPOINT }}
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `cxm-api-key` | CXM API key for authentication | **Yes** | - |
| `cxm-api-endpoint` | CXM API endpoint URL | No | - |
| `tf-entrypoints` | Specific Terraform entrypoint path(s) to scan (comma-separated). If provided, lock file discovery is skipped. | No | - |
| `repository-url` | Repository URL (auto-detected from GitHub context) | No | Auto-detected |
| `verbose` | Enable verbose logging (`true`/`false`) | No | `false` |
| `dry-run` | Enable dry-run mode (parse data without posting to API) | No | `false` |
| `terraform-show-timeout` | Timeout for terraform show in seconds | No | `300` |
| `sensitive-fields` | Comma-separated list of additional sensitive field patterns to redact | No | - |
| `max-retries` | Maximum API retry attempts | No | `3` |
| `timeout-seconds` | API call timeout in seconds | No | `30` |

## Environment Variables

Set these as GitHub repository secrets:

- `CXM_API_KEY` - Your CXM API key (required)
- `CXM_API_ENDPOINT` - Your CXM API endpoint URL (optional)

## Common Issues

### Error: "Scan directory does not exist"

**Problem:** The repository was not checked out.

**Solution:** Add `uses: actions/checkout@v4` before the scan action:

```yaml
steps:
  - uses: actions/checkout@v4  # ← Add this
  - uses: ./path/to/cxm_iac_crawler/integrations/github
    with:
      cxm-api-key: ${{ secrets.CXM_API_KEY }}
```

### Error: "No .terraform.lock.hcl files found"

**Problem:** Terraform has not been initialized.

**Solution:** Either:
1. Commit `.terraform.lock.hcl` files to your repository, or
2. Run `terraform init` before scanning:

```yaml
steps:
  - uses: actions/checkout@v4

  - name: Setup Terraform
    uses: hashicorp/setup-terraform@v3

  - name: Terraform Init
    run: terraform init
    working-directory: ./infrastructure

  - name: Scan Terraform
    uses: ./path/to/cxm_iac_crawler/integrations/github
    with:
      cxm-api-key: ${{ secrets.CXM_API_KEY }}
      tf-entrypoints: 'infrastructure'
```

### Error: "403 Forbidden" from API

**Problem:** Invalid or expired API key.

**Solution:**
1. Verify your `CXM_API_KEY` secret is set correctly
2. Check the API key has not expired
3. Ensure the key has permissions to write to the API

## Security Best Practices

- ✅ **DO** store `CXM_API_KEY` as a GitHub secret
- ✅ **DO** use `permissions: contents: read` to limit workflow permissions
- ✅ **DO** enable verbose logging temporarily for debugging
- ❌ **DON'T** commit API keys to your repository
- ❌ **DON'T** log API keys or sensitive values

## Support

- Main Documentation: [../../README.md](../../README.md)
- Issues: https://github.com/koomo/cxm/issues
