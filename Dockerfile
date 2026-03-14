FROM rust:1.85-slim-bookworm AS builder

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y pkg-config libssl-dev && rm -rf /var/lib/apt/lists/*

COPY . .

RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/src/app/target/release/normalize-album-art /usr/local/bin/normalize-album-art

WORKDIR /music

ENTRYPOINT ["normalize-album-art"]
