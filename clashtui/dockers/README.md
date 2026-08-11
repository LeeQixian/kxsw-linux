# Docker

Alpine OpenRC test container management.

## Usage

```bash
# Build the image
./dockers/manage.py build

# Run the container (detached, mounts project at /workspace/clashtui)
./dockers/manage.py run

# Open a shell in the container
./dockers/manage.py shell

# Run the install script inside the container (openrc mode)
./dockers/manage.py test-install

# Show container status
./dockers/manage.py status

# Show logs
./dockers/manage.py logs         # One-shot
./dockers/manage.py logs -f      # Follow

# Stop and remove the container
./dockers/manage.py stop

# Stop container and remove image
./dockers/manage.py clean --image
```

The script can run from any directory. It locates the project root by searching upwards for `Cargo.toml`.
