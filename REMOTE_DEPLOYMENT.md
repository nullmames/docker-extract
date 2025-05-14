# Remote Deployment Guide

This guide explains how to deploy the Docker Binary Extractor on a remote server using Docker Compose.

## Prerequisites

- A remote server with Docker and Docker Compose installed
- SSH access to the server
- The Docker Binary Extractor container image (built or pulled from registry)

## Deployment Steps

1. **Connect to your server**

   ```bash
   ssh user@your-server-ip
   ```

2. **Create a project directory**

   ```bash
   mkdir -p docker-extractor && cd docker-extractor
   ```

3. **Copy the docker-compose.yml file**

   Either copy the file from your local machine or create it on the server:

   ```bash
   nano docker-compose.yml
   ```

   Then paste the content from the docker-compose.yml file and save.

4. **Create or copy your config.yaml file**

   ```bash
   nano config.yaml
   ```

   Add your configuration for the Docker images and binaries to extract.

5. **Create the data directory**

   ```bash
   mkdir -p data
   ```

6. **Update the image name**

   Edit the docker-compose.yml file to use your actual image name if you've published the image to a registry.

7. **Start the service**

   ```bash
   docker-compose up -d
   ```

8. **Check the logs**

   ```bash
   docker-compose logs -f
   ```

## Configuration Options

You can customize the deployment by modifying the environment variables in the docker-compose.yml file:

- `MODE`: Set to `extract`, `web`, or `both` (default)
- `CHECK_INTERVAL`: How often to check for new binaries (in seconds)
- `CONFIG_REPO`: Optional GitHub repository URL for configuration
- `PROXY_PATH`: Set if running behind a reverse proxy with a path prefix

## Accessing the Web Interface

Once deployed, you can access the web interface at:

```
http://your-server-ip:5050
```

## Using with a Reverse Proxy

If you want to run behind a reverse proxy like Nginx or Traefik, set the `PROXY_PATH` environment variable and configure your proxy accordingly.

Example Nginx configuration:

```nginx
location /extractor/ {
    proxy_pass http://localhost:5050/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Then set `PROXY_PATH=/extractor` in your docker-compose.yml file. 