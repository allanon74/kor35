# Immagine Cloud Agent KOR35 con Docker-in-Docker (DinD).
# Non COPY del monorepo: Cursor checkouta il commit a runtime.
# Riferimento: https://cursor.com/docs/cloud-agent/setup#running-docker
FROM ubuntu:24.04

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Pin docker-ce come nelle docs Cursor; plugin lasciati floating per evitare 404 apt.
ARG DOCKER_VERSION=5:28.5.2-1~ubuntu.24.04~noble

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      apt-transport-https \
      acl \
      bash \
      ca-certificates \
      corkscrew \
      curl \
      fuse-overlayfs \
      git \
      git-lfs \
      gnupg \
      iptables \
      jq \
      less \
      locales \
      make \
      openssh-client \
      procps \
      python3 \
      python3-pip \
      python3-venv \
      rsync \
      sudo \
      tmux \
      unzip \
      wget \
      zip && \
    locale-gen en_US.UTF-8 && \
    git lfs install --system && \
    rm -rf /var/lib/apt/lists/*

# Docker CE + plugin compose/buildx
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl --retry 3 --retry-delay 5 -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      docker-ce=${DOCKER_VERSION} \
      docker-ce-cli=${DOCKER_VERSION} \
      containerd.io \
      docker-buildx-plugin \
      docker-compose-plugin && \
    rm -rf /var/lib/apt/lists/*

# DinD: fuse-overlayfs + iptables-legacy (nested container)
RUN mkdir -p /etc/docker && \
    printf '%s\n' \
      '{' \
      '  "storage-driver": "fuse-overlayfs",' \
      '  "features": {' \
      '    "buildkit": true' \
      '  }' \
      '}' > /etc/docker/daemon.json && \
    update-alternatives --set iptables /usr/sbin/iptables-legacy && \
    update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy

# Utente ubuntu (non-root) con docker + sudo senza password
RUN if ! id -u ubuntu >/dev/null 2>&1; then useradd -m -s /bin/bash ubuntu; fi && \
    groupadd -f docker && \
    usermod -aG docker,sudo ubuntu && \
    echo "ubuntu ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ubuntu && \
    chmod 0440 /etc/sudoers.d/ubuntu

WORKDIR /home/ubuntu
USER ubuntu
