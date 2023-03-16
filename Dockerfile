FROM nvidia/cuda:11.7.1-runtime-ubuntu20.04

RUN apt-get -y update
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install \
      python3.10 \
      python3-pip \
      python3-setuptools \
      ffmpeg \
      redis \
    && rm -rf /var/lib/apt/lists/*

RUN python3.10 -m pip install pipenv==2022.4.8

RUN mkdir -p /opt/whisper
ADD https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt /opt/whisper/base.pt

WORKDIR /opt

COPY Pipfile /opt
COPY Pipfile.lock /opt
RUN pipenv sync

COPY . /opt

EXPOSE 8000
CMD ["pipenv", "run", "uvicorn", "stt_fastapi:app", "--reload"]