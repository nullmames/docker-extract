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

4. **Configure your deployment**

   The docker-compose.yml file provides three configuration methods:
   
   a. **Local configuration file**:
      ```yaml
      volumes:
        - ./config.yaml:/app/config.yaml
      environment:
        - CONFIG_PATH=/app/config.yaml
      ```
   
   b. **Direct URL configuration** (recommended):
      ```yaml
      environment:
        - CONFIG_PATH=https://raw.githubusercontent.com/username/repo/branch/config.yaml
      ```
   
   c. **GitHub repository configuration**:
      ```yaml
      environment:
        - CONFIG_REPO=https://github.com/username/repo
      ```

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

## Configuration Methods

### 1. Local Configuration

This is the traditional method where you create a local `config.yaml` file and mount it into the container. This works well for static configurations.

### 2. Direct URL Configuration (Recommended)

This new method allows you to specify a direct URL to a raw configuration file on GitHub or any other web server.

Example:
```yaml
environment:
  - CONFIG_PATH=https://raw.githubusercontent.com/nullmames/docker-extract/refs/heads/main/config.yaml
```

Benefits:
- No need to mount a local config file
- Configuration is fetched directly from the URL
- Changes to the URL configuration are detected automatically
- Supports any raw URL, not just GitHub repositories

### 3. GitHub Repository Configuration

This legacy method fetches the configuration from a GitHub repository. It's less flexible than the direct URL method as it can only use the `config.yaml` file in the main branch.

```yaml
environment:
  - CONFIG_REPO=https://github.com/username/repo
```

## Other Configuration Options

You can customize the deployment by modifying the environment variables in the docker-compose.yml file:

- `MODE`: Set to `extract`, `web`, or `both` (default)
- `CHECK_INTERVAL`: How often to check for new binaries (in seconds)
- `PROXY_PATH`: Set if running behind a reverse proxy with a path prefix
- `DOCKER_PLATFORM_SUPPORT`: Set to `false` if you encounter platform parameter errors

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

## Troubleshooting

### Platform Parameter Error

If you see errors like:
```
Error processing image: run() got an unexpected keyword argument 'platform'
```

This indicates a compatibility issue between your Docker client version and the Python Docker SDK. To fix this:

1. Set the `DOCKER_PLATFORM_SUPPORT=false` environment variable in your docker-compose.yml file:
   ```yaml
   environment:
     # Other environment variables...
     - DOCKER_PLATFORM_SUPPORT=false
   ```

2. Restart the container:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

This will disable the platform parameter when creating containers, which should resolve the error. 