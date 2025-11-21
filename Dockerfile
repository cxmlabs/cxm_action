FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/koomo/cxm"
LABEL org.opencontainers.image.description="CXM IAC Crawler - Multi-platform Terraform scanner"
LABEL org.opencontainers.image.licenses="Proprietary"

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        unzip \
        git \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install Terraform
ARG TERRAFORM_VERSION=1.9.8
RUN wget -q https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip -d /usr/local/bin && \
    rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    terraform --version

# Install uv for Python package management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy crawler files
COPY pyproject.toml ./
COPY cxm_iac_crawler ./cxm_iac_crawler

# Install the crawler
RUN uv pip install --system --no-cache .

# Copy entrypoint script
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set environment variables defaults
ENV CXM_MAX_RETRIES=3
ENV CXM_TIMEOUT_SECONDS=30
ENV TERRAFORM_SHOW_TIMEOUT=300

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
CMD ["--help"]
