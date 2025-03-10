FROM alpine:3.21
ENV MPICH_VERSION=4.3.0

# Install build dependencies
RUN apk update && \
    apk add --no-cache \
    build-base \
    gcc \
    g++ \
    gfortran \
    make \
    wget \
    perl \
    python3 \
    linux-headers \
    autoconf \
    automake \
    libtool \
    m4 \
    util-linux-dev \
    libnl3-dev \
    rdma-core-dev \
    libudev-zero-dev \
    bsd-compat-headers \
    musl-dev \
    && rm -rf /var/cache/apk/*

# Create workspace directory
WORKDIR /tmp

# Download and install MPICH
RUN wget https://www.mpich.org/static/downloads/${MPICH_VERSION}/mpich-${MPICH_VERSION}.tar.gz && \
    tar -xzf mpich-${MPICH_VERSION}.tar.gz && \
    cd mpich-${MPICH_VERSION} && \
    ./configure --prefix=/usr --enable-fortran=all --with-device=ch3 && \
    make -j$(nproc) && \
    make install && \
    cd .. && \
    rm -rf mpich-${MPICH_VERSION} mpich-${MPICH_VERSION}.tar.gz

# Clean up build dependencies to reduce image size
RUN apk del \
    autoconf \
    automake \
    libtool \
    m4 \
    wget \
    perl \
    && rm -rf /var/cache/apk/*
