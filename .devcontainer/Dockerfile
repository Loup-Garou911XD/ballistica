# Dev container for ballistica. Same toolchain as the docker build in
# pconfig/docker/Dockerfile (keep the two package lists in sync), plus
# git and pkg-config for day-to-day work.
#
# Ubuntu 26.04 is the first LTS shipping python3.14, which the build
# requires exactly (see ballisticakit-cmake/CMakeLists.txt).
FROM ubuntu:26.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        clang \
        clang-format \
        cmake \
        curl \
        git \
        libglut-dev \
        libopenal-dev \
        libpango1.0-dev \
        libsdl3-dev \
        libvorbis-dev \
        libzstd-dev \
        make \
        pkg-config \
        python3-pip \
        python3.14-dev \
        python3.14-venv \
        rsync \
        zstd && \
    rm -rf /var/lib/apt/lists/*

# uv is what `make env` uses to build the project venv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
