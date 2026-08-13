FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir claude-agent-sdk

RUN groupadd -g 1000 claude && useradd -u 1000 -g claude -m claude

COPY SKILL.md gerrit_review.py reference.md review_agent.py \
     /opt/openstack-review/

RUN chown -R claude:claude /opt/openstack-review

# Run with --userns=keep-id to map host UID into the container
VOLUME /output

USER claude

ENTRYPOINT ["python3", "/opt/openstack-review/review_agent.py", "--output-dir", "/output"]
