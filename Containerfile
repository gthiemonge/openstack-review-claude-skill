FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create user
RUN groupadd -g 1000 claude && useradd -u 1000 -g claude -m claude

# Copy package files
WORKDIR /app
COPY pyproject.toml setup.py MANIFEST.in requirements.txt ./
COPY src/ ./src/
COPY SKILL.md reference.md ./

# Install package
RUN pip install --no-cache-dir .

# Switch to non-root user
USER claude

# Set working directory for reviews
WORKDIR /workspace

# Volume for output
VOLUME /output

# Default entrypoint
ENTRYPOINT ["openstack-review", "--output-dir", "/output"]
