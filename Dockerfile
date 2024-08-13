FROM python:3.12.4-alpine

ARG GOOSEBIT_VERSION

#RUN pip install --no-cache-dir goosebit[postgresql]==$GOOSEBIT_VERSION

RUN apk add --no-cache git && pip install --no-cache-dir git+https://github.com/husqvarnagroup/uvicorn.git@gardena/eb/proxy_headers

COPY . /tmp/src
RUN cd /tmp/src && \
    pip install --no-cache-dir remote-pdb && \
    pip install --no-cache-dir .[postgresql] && \
    cd - && \
    rm -rf /tmp/src

VOLUME /artifacts

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips=*", "goosebit:app"]
