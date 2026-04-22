FROM jupyter/base-notebook

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openjdk-11-jdk \
        curl \
        unzip \
        build-essential \
        pkg-config \
        libpoppler-cpp-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir jupyterlab && \
    curl -L https://github.com/SpencerPark/IJava/releases/download/v1.3.0/ijava-1.3.0.zip -o ijava.zip && \
    unzip ijava.zip && \
    python install.py && \
    rm -rf ijava.zip ijava && \
    pip install --no-cache-dir -U sec-certs && \
    python -m spacy download en_core_web_sm

USER $NB_UID