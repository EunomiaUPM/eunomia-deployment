# Runtime for the eunomia CLI on machines without Python 3.8+: Python and the
# Docker CLI with the compose plugin. The CLI itself is not copied in: the
# wrappers (./eunomia, eunomia.cmd, eunomia.ps1) mount the checkout and run it
# from there, so a git pull needs no rebuild.
#
# Built by the wrappers on first use:
#   docker build -t eunomia-tools:1 deployment/tools
FROM python:3.12-alpine3.20
RUN apk add --no-cache docker-cli docker-cli-compose
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
