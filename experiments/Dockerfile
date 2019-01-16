FROM ubuntu:16.04

# add docker user
RUN apt-get update \
 && apt-get install -y --no-install-recommends sudo \
 && useradd -ms /bin/bash docker \
 && echo 'docker ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && usermod -aG sudo docker \
 && chown -R docker /usr/local/bin \
 && sudo apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
USER docker

RUN sudo apt-get update \
 && sudo apt-get install -y --no-install-recommends \
      python \
      python-pip \
      python-dev \
      git \
      gcc \
      g++ \
      build-essential \
      libxml2-dev \
      libxslt-dev \
      libexpat1-dev \
      make \
      cmake \
      libtool \
      automake \
      autoconf \
      libfreetype6-dev \
      libpng-dev \
      liblapack-dev \
      gfortran \
      ca-certificates \
      openssl \
      wget \
 && sudo apt-get clean \
 && sudo rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install packages
# FIXME this is a build-time dependency
RUN pip install --no-cache-dir --upgrade pip==9.0.3 \
 && pip install --user --no-cache-dir setuptools wheel \
 && pip install --user --no-cache-dir \
      matplotlib \
      pyserial \
      scipy \
      pexpect \
      future \
      mavproxy \
      gcovr \
      pymavlink==2.2.10

# install bear
RUN cd /tmp \
 && wget -nv https://github.com/rizsotto/Bear/archive/2.3.11.tar.gz \
 && tar -xf 2.3.11.tar.gz \
 && cd Bear-2.3.11 \
 && mkdir build \
 && cd build \
 && cmake .. \
 && make all \
 && sudo make install \
 && rm -rf /tmp/*

# Copter-3.6.4
RUN sudo mkdir -p /opt \
 && sudo chown -R docker /opt \
 && git clone https://github.com/ArduPilot/ardupilot /opt/ardupilot \
 && cd /opt/ardupilot \
 && git checkout Copter-3.6.4 \
 && ./waf configure \
 && ./waf configure \
 && bear ./waf build -j8
COPY copter.parm /opt/ardupilot/copter.parm
WORKDIR /opt/ardupilot

ENV PATH "${PATH}:/opt/ardupilot/Tools/autotest"

# Unfortunately, we need to build Dronekit from source to avoid the
# dependency hell created by the latest stable release on PyPI.
RUN git clone https://github.com/dronekit/dronekit-python /tmp/dronekit \
 && git clone https://github.com/dronekit/dronekit-sitl /tmp/dronekit-sitl \
 && cd /tmp/dronekit \
 && git checkout a20eadf92b5d30940a7533a8a57a39273cdf3938 \
 && pip install --no-cache-dir --user . \
 && cd /tmp/dronekit-sitl \
 && git checkout 9a2d6592f7844d7df17d417cd33a9de8386cdaae \
 && pip install --no-cache-dir --user . \
 && rm -rf /tmp/*
ENV PATH "/home/docker/.local/bin:${PATH}"
