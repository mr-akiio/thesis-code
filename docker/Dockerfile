FROM jupyter/base-notebook

USER root

# =========================
# 1. System dependencies
# =========================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openjdk-11-jdk \
        curl \
        git \
        unzip \
        build-essential \
        pkg-config \
        libpoppler-cpp-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# =========================
# 2. Python dependencies (core)
# =========================
RUN pip install --no-cache-dir \
    jupyterlab==4.* \
    notebook==7.* \
    spacy==3.*

# =========================
# 3. sec-certs (pinned to commit)
# =========================
RUN pip install --no-cache-dir \
    git+https://github.com/crocs-muni/sec-certs.git@8ab79f0c7

# =========================
# 4. spaCy model (explicit versioning style)
# =========================
RUN python -m spacy download en_core_web_sm

# =========================
# 5. Java kernel (IJava)
# =========================
RUN curl -L https://github.com/SpencerPark/IJava/releases/download/v1.3.0/ijava-1.3.0.zip -o /tmp/ijava.zip && \
    unzip /tmp/ijava.zip -d /tmp/ijava && \
    python /tmp/ijava/install.py && \
    rm -rf /tmp/ijava /tmp/ijava.zip

USER $NB_UID
WORKDIR /home/jovyan/work