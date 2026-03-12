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
    cmake \
    libyaml-cpp-dev \
    libboost-all-dev \
    python3 \
    python3-pip \
    git \
    screen \
    vim \
    valgrind \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for plotting
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt
