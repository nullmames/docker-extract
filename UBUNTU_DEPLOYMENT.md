# Ubuntu Server Deployment Guide

This guide explains how to deploy the Docker Binary Extractor on an Ubuntu server.

## Prerequisites

- Ubuntu server (18.04, 20.04, 22.04, or newer)
- SSH access with sudo privileges
- Internet connectivity for package installation

## Initial Server Setup

1. **Connect to your Ubuntu server**

   ```bash
   ssh user@your-server-ip
   ```

2. **Update the system**

   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **Install Docker**

   If Docker is not already installed:

   ```bash
   # Install required packages
   sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

   # Add Docker's official GPG key
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

   # Add the Docker repository
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

   # Update package database with Docker packages
   sudo apt update

   # Install Docker
   sudo apt install -y docker-ce docker-ce-cli containerd.io

   # Add your user to the docker group to run Docker without sudo
   sudo usermod -aG docker $USER

   # Apply group changes (you'll need to log out and back in for this to take effect)
   newgrp docker
   ```

4. **Install Docker Compose**

   ```bash
   # Install Docker Compose
   sudo apt install -y docker-compose-plugin
   
   # Create a symbolic link for compatibility
   sudo ln -s /usr/libexec/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose
   
   # Verify installation
   docker compose version
   ```

## Deploy Docker Binary Extractor

1. **Create a project directory**

   ```bash
   mkdir -p docker-extractor && cd docker-extractor
   ```

2. **Create docker-compose.yml file**

   ```bash
   nano docker-compose.yml
   ```

   Paste the following configuration exactly as shown, maintaining the same indentation (spaces, not tabs):

   ```yaml
   version: '3.8'

   services:
     docker-extractor:
       image: ghcr.io/nullmames/docker-extract:v1.1.1
       container_name: docker-extractor
       restart: unless-stopped
       volumes:
         - /var/run/docker.sock:/var/run/docker.sock
         - ./data:/data
       ports:
         - "5050:5050"
       environment:
         - MODE=both
         - CONFIG_PATH=https://raw.githubusercontent.com/nullmames/docker-extract/refs/heads/main/config.yaml
         - OUTPUT_DIR=/data
         - CHECK_INTERVAL=3600
         - DOCKER_PLATFORM_SUPPORT=false
       networks:
         - extractor-network

   networks:
     extractor-network:
       driver: bridge
   ```

   Save the file by pressing `Ctrl+X`, then `Y`, then `Enter`.

   > **Note**: If you encounter YAML errors like `yaml: line 2: did not find expected key`, make sure:
   > - Your text editor is using spaces (not tabs)
   > - There are no extra spaces at the beginning of any line
   > - You copied the entire text including the first `version:` line

3. **Alternatively, download the file directly**

   If you're having issues with formatting, you can download the file directly:

   ```bash
   wget -O docker-compose.yml https://raw.githubusercontent.com/nullmames/docker-extract/main/docker-compose.example.yml
   ```

4. **Create the data directory**

   ```bash
   mkdir -p data
   ```

5. **Start the service**

   ```bash
   docker compose up -d
   ```

6. **Check logs**

   ```bash
   docker compose logs -f
   ```

## Ubuntu-specific Firewall Configuration

If UFW (Uncomplicated Firewall) is enabled, you need to open the web interface port:

```bash
sudo ufw allow 5050/tcp
sudo ufw reload
```

## Setting Up as a System Service

For automatic startup on system boot, create a systemd service:

1. **Create a service file**

   ```bash
   sudo nano /etc/systemd/system/docker-extractor.service
   ```

   Add the following content:

   ```ini
   [Unit]
   Description=Docker Binary Extractor
   After=docker.service
   Requires=docker.service

   [Service]
   Type=oneshot
   RemainAfterExit=yes
   WorkingDirectory=/path/to/docker-extractor
   ExecStart=/usr/local/bin/docker-compose up -d
   ExecStop=/usr/local/bin/docker-compose down
   TimeoutStartSec=0

   [Install]
   WantedBy=multi-user.target
   ```

   Replace `/path/to/docker-extractor` with your actual path.

2. **Enable and start the service**

   ```bash
   sudo systemctl enable docker-extractor.service
   sudo systemctl start docker-extractor.service
   ```

## Nginx Reverse Proxy Configuration (Optional)

If you want to run the application behind Nginx:

1. **Install Nginx**

   ```bash
   sudo apt install -y nginx
   ```

2. **Create a new site configuration**

   ```bash
   sudo nano /etc/nginx/sites-available/docker-extractor
   ```

   Add the following configuration:

   ```nginx
   server {
       listen 80;
       server_name your-domain.com;  # Replace with your domain or server IP

       location /extractor/ {
           proxy_pass http://localhost:5050/;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **Enable the site**

   ```bash
   sudo ln -s /etc/nginx/sites-available/docker-extractor /etc/nginx/sites-enabled/
   sudo nginx -t  # Test configuration
   sudo systemctl reload nginx
   ```

4. **Update the docker-compose.yml file**

   Add the `PROXY_PATH` environment variable:

   ```yaml
   environment:
     # Other environment variables...
     - PROXY_PATH=/extractor
   ```

5. **Restart the container**

   ```bash
   docker compose down
   docker compose up -d
   ```

## Troubleshooting Ubuntu-specific Issues

### Permission Issues

If you encounter permission issues with the Docker socket:

```bash
# Ensure your user is in the docker group
sudo usermod -aG docker $USER
newgrp docker

# Check socket permissions
ls -la /var/run/docker.sock
# Should show: srw-rw---- 1 root docker
```

### Memory Limitations

For Ubuntu servers with limited memory:

```bash
# Add memory limit to the service in docker-compose.yml
services:
  docker-extractor:
    # Other configuration...
    deploy:
      resources:
        limits:
          memory: 512M
```

### Disk Space Monitoring

Set up monitoring for disk space as Docker images can consume significant space:

```bash
# Install monitoring tools
sudo apt install -y ncdu htop

# Check disk usage
ncdu /var/lib/docker
```

### Log Rotation

Set up log rotation for Docker logs:

```bash
sudo nano /etc/docker/daemon.json
```

Add:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Restart Docker:
```bash
sudo systemctl restart docker
``` 