FROM openjdk:11.0.8-jre-buster as builder
WORKDIR /build/
COPY . /build/
RUN /build/generate.sh


FROM python:3.10.4-alpine3.15
WORKDIR /app
ENTRYPOINT ["python3"]
CMD ["-m", "opera.api.cli"]

COPY requirements.txt /app/
COPY requirements-dev.txt /app/

RUN export CRYPTOGRAPHY_PREREQS="gcc musl-dev libffi-dev openssl-dev python3-dev" \
    && export PIP_PREREQS="git" \
    && apk add $CRYPTOGRAPHY_PREREQS $PIP_PREREQS \
    && pip3 install --upgrade pip \
    && pip3 install --no-cache-dir cryptography==3.3.2 \
    && pip3 install --no-cache-dir wheel \
    && pip3 install --no-cache-dir -r requirements.txt \
    && pip3 install --no-cache-dir -r requirements-dev.txt \
    && apk del $CRYPTOGRAPHY_PREREQS $PIP_PREREQS \
    && rm requirements.txt requirements-dev.txt

COPY --from=builder /build/src/ /app/
