#!/usr/bin/env bash
set -e

DOCKER_BASE_IMAGE="${DOCKER_BASE_IMAGE:-python:slim}"

# Generate a Docker base image so we can use different Pythons
cat > test-base.dockerfile <<EOF
FROM $DOCKER_BASE_IMAGE

# Copy in the source
COPY . /pydexec
WORKDIR /pydexec

# Install it
RUN pip install --no-cache -e .
EOF

# Build the generated Dockerfile
docker build -t pydexec:test-base -f test-base.dockerfile .

# Run the gosu tests
docker build -t pydexec:pysu-test -f pysu-test.dockerfile .
