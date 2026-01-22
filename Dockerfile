FROM certbot/certbot:latest

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    python3-dev

# Copy plugin source
COPY . /opt/certbot-dns-opusdns

# Install plugin
RUN pip install --no-cache-dir /opt/certbot-dns-opusdns

# Set working directory
WORKDIR /etc/letsencrypt

# Default command
ENTRYPOINT ["/usr/local/bin/certbot"]
CMD ["--help"]
