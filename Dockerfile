FROM python:3.9-alpine

RUN apk add --no-cache ffmpeg opus-dev libsodium-dev python3-dev g++ make && rm -rf /var/cache/apk/*

WORKDIR /app

ENV LD_LIBRARY_PATH=/usr/lib

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt --pre

COPY . .

EXPOSE 8080

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]