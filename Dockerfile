FROM python:3.11-slim-bookworm

WORKDIR /app

# Install btrfs-progs (required for ASG to interact with the filesystem)
RUN apt-get update && apt-get install -y --no-install-recommends \
    btrfs-progs \
    && rm -rf /var/lib/apt/lists/*

# !! SECURITY NOTICE !!
# ASG requires root/privileged access to run BTRFS commands. 
# The container must be run with --privileged or as the root user.
# It also needs access to the host's /proc filesystem and the target BTRFS mount.
#
# Minimal run example:
#   docker run -d \
#     --name asg \
#     --privileged \
#     -v /proc:/proc:ro \
#     -v /mnt/media_pool:/mnt/media_pool \
#     -v /etc/asg/config.yaml:/app/config.yaml:ro \
#     ghcr.io/jaldertech/asg asg status

# Install the package
COPY . .
RUN pip install --no-cache-dir .

# Default command
ENTRYPOINT ["asg"]
CMD ["status"]
