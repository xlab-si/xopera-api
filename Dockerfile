FROM openjdk:11.0.7-jre-slim-buster as builder
WORKDIR /build/
COPY . /build/
RUN /build/generate.sh


FROM python:3.8.2-alpine3.11
WORKDIR /app
ENTRYPOINT ["python3"]
CMD ["-m", "opera.api.cli"]

COPY requirements.txt /app/

RUN pip3 install --no-cache-dir wheel \
    && export CRYPTOGRAPHY_PREREQS="gcc musl-dev libffi-dev openssl-dev python3-dev" \
    && apk add $CRYPTOGRAPHY_PREREQS \
    && pip3 install --no-cache-dir -r requirements.txt \
    && apk del $CRYPTOGRAPHY_PREREQS \
    && rm requirements.txt

COPY --from=builder /build/src/ /app/
