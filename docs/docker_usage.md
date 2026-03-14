# Docker Usage Guide

This guide explains how to use the `normalize-album-art` CLI tool using Docker and Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your system.
- [Docker Compose](https://docs.docker.com/compose/install/) (included with Docker Desktop).

## Getting Started

### 1. Prepare your music folder

Place the music you want to process in a folder named `music` within the project root, or modify the `docker-compose.yml` to point to your existing music directory.

By default, the `docker-compose.yml` is configured as follows:
```yaml
volumes:
  - ./music:/music
```

### 2. Build and Run

To process the music in the `./music` folder with default settings (500x500):

```bash
docker compose run --rm normalize-art
```

### 3. Customizing the Run

You can pass extra arguments to the CLI tool (like `--size`) by appending them to the command:

```bash
# Set a custom size of 800x800
docker compose run --rm normalize-art /music --size 800
```

### 4. Rebuilding the image

If you modify the source code, you should rebuild the Docker image:

```bash
docker compose build
```

## How it works

- The `Dockerfile` uses a multi-stage build to compile the Rust application and then copies the binary to a slim Debian image to minimize size.
- The `docker-compose.yml` mounts your local music folder into the `/music` directory inside the container and executes the tool against that path.
