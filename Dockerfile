FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/mjfxjas/aws_automations"
LABEL org.opencontainers.image.description="AWS resource cleanup and automation utilities"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install aws-automations from PyPI
RUN pip install --no-cache-dir aws-automations

# Create non-root user
RUN useradd -m -u 1000 awsuser && chown -R awsuser:awsuser /app
USER awsuser

ENTRYPOINT ["aws-cleanup"]
CMD ["--help"]
