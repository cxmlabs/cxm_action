# GitLab CI Integration

CXM IAC Crawler for GitLab CI pipelines.

## Usage

**Note:** GitLab CI automatically clones your repository, so no additional checkout step is needed.

### Basic Example

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/koomo/cxm/main/src/cxm-crawlers/cxm_iac_crawler/integrations/gitlab/.gitlab-ci.yml'

cxm-terraform-scan:
  extends: .cxm_iac_scan
  variables:
    CXM_API_KEY: ${CXM_API_KEY}
    CXM_API_ENDPOINT: ${CXM_API_ENDPOINT}
```

### Manual Configuration

If you prefer not to use the template:

```yaml
terraform-scan:
  stage: scan
  image: ghcr.io/koomo/cxm-iac-crawler:latest
  variables:
    CXM_API_KEY: ${CXM_API_KEY}
    CXM_API_ENDPOINT: ${CXM_API_ENDPOINT}
    INPUT_VERBOSE: "true"
  script:
    - echo "Terraform scan completed"
  rules:
    - if: $CI_PIPELINE_SOURCE == "push"
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

## Environment Variables

Set these in GitLab CI/CD settings (Settings → CI/CD → Variables):

### Required

- `CXM_API_KEY` - Your CXM API key

### Optional

- `CXM_API_ENDPOINT` - Your CXM API endpoint URL
- `INPUT_TF_ENTRYPOINTS` - Specific Terraform entrypoint path(s) to scan (comma-separated)
- `INPUT_VERBOSE` - Enable verbose logging (`true`/`false`, default: `false`)
- `INPUT_DRY_RUN` - Enable dry-run mode (default: `false`)
- `TERRAFORM_SHOW_TIMEOUT` - Terraform show timeout in seconds (default: `300`)
- `SENSITIVE_FIELDS` - Comma-separated list of additional sensitive field patterns to redact
- `CXM_MAX_RETRIES` - Maximum API retry attempts (default: `3`)
- `CXM_TIMEOUT_SECONDS` - API call timeout in seconds (default: `30`)

## Common Issues

### Error: "No .terraform.lock.hcl files found"

**Problem:** Terraform has not been initialized.

**Solution:** Run `terraform init` before scanning:

```yaml
terraform-scan:
  stage: scan
  image: ghcr.io/koomo/cxm-iac-crawler:latest
  variables:
    CXM_API_KEY: ${CXM_API_KEY}
  before_script:
    - cd infrastructure
    - terraform init
  script:
    - cd $CI_PROJECT_DIR
    - cxm-iac-crawler infrastructure
```

### Error: "403 Forbidden" from API

**Problem:** Invalid or expired API key.

**Solution:**
1. Verify your `CXM_API_KEY` variable is set correctly in GitLab CI/CD settings
2. Ensure the variable is not masked if it contains special characters
3. Check the API key has permissions to write to the API

## Security Best Practices

- ✅ **DO** store `CXM_API_KEY` as a masked CI/CD variable
- ✅ **DO** set variable protection for production branches
- ✅ **DO** use environment-specific variables for different stages
- ❌ **DON'T** commit API keys to your repository
- ❌ **DON'T** expose API keys in logs

## Repository Paths

GitLab CI automatically sets these environment variables:

- `CI_PROJECT_DIR` - Root directory of the cloned repository
- `CI_BUILDS_DIR` - Parent directory of all builds

The crawler automatically scans `CI_PROJECT_DIR` by default.

## Support

- Main Documentation: [../../README.md](../../README.md)
- GitLab CI Docs: https://docs.gitlab.com/ee/ci/
- Issues: https://github.com/koomo/cxm/issues
