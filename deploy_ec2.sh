#!/bin/bash
# AWS EC2 Docker Deployment Script for SYNQ Backend
# This script is intended to be run ON your AWS EC2 instance (Ubuntu Server).

# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting SYNQ backend deployment setup..."

# 1. Update packages and install prerequisites
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release git

# 2. Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 3. Set up the Docker repository
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Install Docker Engine and Docker Compose
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. Start Docker and enable it to run at boot
sudo systemctl enable docker
sudo systemctl start docker

# Add current user to the docker group so you don't need 'sudo' for docker commands
sudo usermod -aG docker $USER
echo "Docker installed successfully."

# 6. Cloning/Preparing repository
echo "Setup complete! Please ensure your project is cloned on the server."
echo "If you have already cloned your project, navigate to the folder containing docker-compose.yml and run:"
echo "    docker compose up -d --build"
echo ""
echo "Note: Make sure to copy your .env files into each service directory before running docker compose."
echo "Please LOG OUT and LOG BACK IN to apply the docker group changes to your user."
