#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect CI/CD platform
detect_platform() {
    if [ -n "$GITHUB_ACTIONS" ]; then
        echo "github"
    elif [ -n "$GITLAB_CI" ]; then
        echo "gitlab"
    else
        echo "generic"
    fi
}

# Extract repository URL based on platform
get_repository_url() {
    local platform=$1

    case $platform in
        github)
            echo "${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY}"
            ;;
        gitlab)
            echo "$CI_PROJECT_URL"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Main execution
main() {
    log_info "CXM IAC Crawler Docker Container"

    # Detect platform
    PLATFORM=$(detect_platform)
    log_info "Detected CI/CD Platform: $PLATFORM"

    # Validate required environment variables
    if [ -z "$CXM_API_KEY" ]; then
        log_error "CXM_API_KEY environment variable is required"
        exit 1
    fi

    if [ -z "$CXM_API_ENDPOINT" ]; then
        log_warn "CXM_API_ENDPOINT not set, using default"
    fi

    # Determine repository URL
    REPO_URL="${INPUT_REPOSITORY_URL:-$(get_repository_url $PLATFORM)}"

    if [ -n "$REPO_URL" ]; then
        log_info "Repository URL: $REPO_URL"
    else
        log_warn "Could not determine repository URL automatically"
    fi

    # Use INPUT_SCAN_PATH if provided, otherwise scan current directory
    SCAN_DIR="${INPUT_SCAN_PATH:-.}"

    # Validate current directory has content
    if [ ! "$(ls -A $SCAN_DIR 2>/dev/null)" ]; then
        log_error "Current directory is empty"
        log_error ""
        log_error "For CI/CD usage:"
        log_error "  - GitHub Actions: Add 'uses: actions/checkout@v4' before this action"
        log_error "  - GitLab CI: Repository is auto-cloned"
        log_error ""
        log_error "For local/Docker usage:"
        log_error "  docker run -v \$(pwd):/app -e CXM_API_KEY=... ghcr.io/koomo/cxm-iac-crawler:latest"
        exit 1
    fi

    log_info "Scanning directory: $SCAN_DIR"

    # Show some info about what we found
    if [ -d "$SCAN_DIR/.git" ]; then
        CURRENT_BRANCH=$(cd "$SCAN_DIR" && git branch --show-current 2>/dev/null || echo "unknown")
        CURRENT_SHA=$(cd "$SCAN_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")
        log_info "Git repository detected - branch: $CURRENT_BRANCH, commit: $CURRENT_SHA"
    fi

    # Build crawler command
    CRAWLER_CMD="cxm-iac-crawler"

    # Add platform detection
    CRAWLER_CMD="$CRAWLER_CMD --platform \"$PLATFORM\""

    # Add verbose flag if requested
    if [ "${INPUT_VERBOSE:-false}" = "true" ]; then
        CRAWLER_CMD="$CRAWLER_CMD --verbose"
    fi

    # Add repository URL if available
    if [ -n "$REPO_URL" ]; then
        CRAWLER_CMD="$CRAWLER_CMD --repository-url \"$REPO_URL\""
    fi

    # Add tf-entrypoints if provided
    if [ -n "${INPUT_TF_ENTRYPOINTS}" ]; then
        CRAWLER_CMD="$CRAWLER_CMD --tf-entrypoints \"${INPUT_TF_ENTRYPOINTS}\""
    fi

    # Add scan directory
    CRAWLER_CMD="$CRAWLER_CMD \"$SCAN_DIR\""

    log_info "Executing: $CRAWLER_CMD"

    # Execute the crawler
    eval $CRAWLER_CMD

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        log_info "✓ Scan completed successfully"
    else
        log_error "✗ Scan failed with exit code: $EXIT_CODE"
    fi

    exit $EXIT_CODE
}

# If no arguments provided or first argument is --help, show help
if [ $# -eq 0 ] || [ "$1" = "--help" ]; then
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  CXM IAC Crawler - Multi-Platform Terraform Scanner           ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "This container automatically detects CI/CD platforms and scans"
    echo "Terraform configurations in your repository."
    echo ""
    echo "┌─ Required Environment Variables ─────────────────────────────┐"
    echo "│ CXM_API_KEY             API key for authentication           │"
    echo "└──────────────────────────────────────────────────────────────┘"
    echo ""
    echo "┌─ Optional Environment Variables ─────────────────────────────┐"
    echo "│ CXM_API_ENDPOINT        CXM API endpoint URL                 │"
    echo "│ INPUT_REPOSITORY_URL    Repository URL (auto-detected)       │"
    echo "│ INPUT_VERBOSE           Enable verbose logging (true/false)  │"
    echo "│ CXM_MAX_RETRIES         Max API retry attempts (default: 3)  │"
    echo "│ CXM_TIMEOUT_SECONDS     API timeout in seconds (default: 30) │"
    echo "│ TERRAFORM_SHOW_TIMEOUT  Terraform timeout (default: 300)     │"
    echo "└──────────────────────────────────────────────────────────────┘"
    echo ""
    echo "┌─ Supported CI/CD Platforms ──────────────────────────────────┐"
    echo "│ ✓ GitHub Actions                                             │"
    echo "│ ✓ GitLab CI                                                  │"
    echo "│ ✓ Generic (any platform with Docker)                         │"
    echo "└──────────────────────────────────────────────────────────────┘"
    echo ""
    echo "┌─ Usage Examples ─────────────────────────────────────────────┐"
    echo "│                                                               │"
    echo "│ Local/Docker:                                                 │"
    echo "│   docker run -e CXM_API_KEY=\$KEY \\                          │"
    echo "│     -v \$(pwd):/app \\                                         │"
    echo "│     ghcr.io/koomo/cxm-iac-crawler:latest                     │"
    echo "│                                                               │"
    echo "│ GitHub Actions:                                               │"
    echo "│   - uses: actions/checkout@v4                                │"
    echo "│   - uses: .../integrations/github                            │"
    echo "│     with:                                                     │"
    echo "│       cxm-api-key: \${{ secrets.CXM_API_KEY }}               │"
    echo "│                                                               │"
    echo "│ GitLab CI: Repository auto-cloned (see docs)                 │"
    echo "│                                                               │"
    echo "└──────────────────────────────────────────────────────────────┘"
    echo ""
    echo "Documentation: https://github.com/koomo/cxm/tree/main/src/cxm-crawlers/cxm_iac_crawler"
    echo ""
    exit 0
fi

# Run main function
main "$@"
