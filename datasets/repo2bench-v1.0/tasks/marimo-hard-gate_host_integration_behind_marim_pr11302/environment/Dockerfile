FROM repo2bench/python-base:3.12

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/workspace:/workspace/pydantic_ai_slim:/workspace/pydantic_graph:/workspace/src/pydantic_ai_harness:/workspace/src/pydantic_clai2"

WORKDIR /workspace
COPY workspace.tar.gz /tmp/workspace.tar.gz
RUN tar -xzf /tmp/workspace.tar.gz -C /workspace && \
    rm -f /tmp/workspace.tar.gz && \
    git config --global user.email "bench@repo2bench.local" && \
    git config --global user.name "repo2bench" && \
    git config --global --add safe.directory /workspace && \
    git init -q && git add -A && git commit -q -m "baseline (marimo-team/marimo)" && \
    chmod -R a+rwX /workspace
