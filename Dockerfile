FROM ubuntu:22.04

# LABEL about the custom image
LABEL maintainer="juko6110@colorado.edu"
LABEL version="0.2"
LABEL description="This is custom Docker Image for explanation guided Conflict Based Search."

# Disable Prompt During Packages Installation
ARG DEBIAN_FRONTEND=noninteractive

# Update Ubuntu Software repository and install required packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libyaml-cpp-dev \
    libboost-all-dev \
    python3 \
    python3-pip \
    pkgconf \
    git \
    screen \
    vim \
    valgrind \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install newer CMake via pip (Ubuntu 22.04 ships 3.22, need 3.25+)
RUN pip3 install --no-cache-dir cmake --upgrade

# Ensure pip-installed cmake takes precedence over system cmake
ENV PATH="/usr/local/bin:$PATH"

# Install Python dependencies for plotting
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt