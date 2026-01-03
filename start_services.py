#!/usr/bin/env python3
"""
start_services.py

This script starts the local AI stack with proper initialization for all services.
"""

import os
import subprocess
import time
import argparse
import platform
import sys

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def stop_existing_containers(profiles=None):
    """Stop and remove existing containers."""
    print("Stopping and removing existing containers for project 'localai'...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profiles:
        for profile in profiles:
            if profile != "none":
                cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml", "down"])
    run_command(cmd)

def start_services(profiles=None, environment=None, memory_optimized=False):
    """Start all local AI services."""
    print("Starting local AI services...")
    if memory_optimized:
        print("Memory optimization enabled - applying resource limits")
    cmd = ["docker", "compose", "-p", "localai"]
    if profiles:
        for profile in profiles:
            if profile != "none":
                cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    if memory_optimized:
        cmd.extend(["-f", "docker-compose.override.memory-optimized.yml"])
    cmd.extend(["up", "-d"])
    run_command(cmd)

def generate_searxng_secret_key():
    """Generate a secret key for SearXNG based on the current platform."""
    print("Checking SearXNG settings...")

    # Define paths for SearXNG settings files
    settings_path = os.path.join("searxng", "settings.yml")
    settings_base_path = os.path.join("searxng", "settings-base.yml")

    # Check if settings-base.yml exists
    if not os.path.exists(settings_base_path):
        print(f"Warning: SearXNG base settings file not found at {settings_base_path}")
        return

    # Check if settings.yml exists, if not create it from settings-base.yml
    if not os.path.exists(settings_path):
        print(f"SearXNG settings.yml not found. Creating from {settings_base_path}...")
        try:
            shutil.copyfile(settings_base_path, settings_path)
            print(f"Created {settings_path} from {settings_base_path}")
        except Exception as e:
            print(f"Error creating settings.yml: {e}")
            return
    else:
        print(f"SearXNG settings.yml already exists at {settings_path}")

    print("Generating SearXNG secret key...")

    # Detect the platform and run the appropriate command
    system = platform.system()

    try:
        if system == "Windows":
            print("Detected Windows platform, using PowerShell to generate secret key...")
            # PowerShell command to generate a random key and replace in the settings file
            ps_command = [
                "powershell", "-Command",
                "$randomBytes = New-Object byte[] 32; " +
                "(New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes); " +
                "$secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ }); " +
                "(Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml"
            ]
            subprocess.run(ps_command, check=True)

        elif system == "Darwin":  # macOS
            print("Detected macOS platform, using sed command with empty string parameter...")
            # macOS sed command requires an empty string for the -i parameter
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", "", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)

        else:  # Linux and other Unix-like systems
            print("Detected Linux/Unix platform, using standard sed command...")
            # Standard sed command for Linux
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)

        print("SearXNG secret key generated successfully.")

    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")
        print("You may need to manually generate the secret key using the commands:")
        print("  - Linux: sed -i \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" searxng/settings.yml")
        print("  - macOS: sed -i '' \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" searxng/settings.yml")
        print("  - Windows (PowerShell):")
        print("    $randomBytes = New-Object byte[] 32")
        print("    (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes)")
        print("    $secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ })")
        print("    (Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml")

def check_and_fix_docker_compose_for_searxng():
    """Check and modify docker-compose.yml for SearXNG first run."""
    docker_compose_path = "docker-compose.yml"
    if not os.path.exists(docker_compose_path):
        print(f"Warning: Docker Compose file not found at {docker_compose_path}")
        return

    try:
        # Read the docker-compose.yml file
        with open(docker_compose_path, 'r') as file:
            content = file.read()

        # Default to first run
        is_first_run = True

        # Check if Docker is running and if the SearXNG container exists
        try:
            # Check if the SearXNG container is running
            container_check = subprocess.run(
                ["docker", "ps", "--filter", "name=searxng", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            searxng_containers = container_check.stdout.strip().split('\n')

            # If SearXNG container is running, check inside for uwsgi.ini
            if any(container for container in searxng_containers if container):
                container_name = next(container for container in searxng_containers if container)
                print(f"Found running SearXNG container: {container_name}")

                # Check if uwsgi.ini exists inside the container
                container_check = subprocess.run(
                    ["docker", "exec", container_name, "sh", "-c", "[ -f /etc/searxng/uwsgi.ini ] && echo 'found' || echo 'not_found'"],
                    capture_output=True, text=True, check=False
                )

                if "found" in container_check.stdout:
                    print("Found uwsgi.ini inside the SearXNG container - not first run")
                    is_first_run = False
                else:
                    print("uwsgi.ini not found inside the SearXNG container - first run")
                    is_first_run = True
            else:
                print("No running SearXNG container found - assuming first run")
        except Exception as e:
            print(f"Error checking Docker container: {e} - assuming first run")

        if is_first_run and "cap_drop: - ALL" in content:
            print("First run detected for SearXNG. Temporarily removing 'cap_drop: - ALL' directive...")
            # Temporarily comment out the cap_drop line
            modified_content = content.replace("cap_drop: - ALL", "# cap_drop: - ALL  # Temporarily commented out for first run")

            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)

            print("Note: After the first run completes successfully, you should re-add 'cap_drop: - ALL' to docker-compose.yml for security reasons.")
        elif not is_first_run and "# cap_drop: - ALL  # Temporarily commented out for first run" in content:
            print("SearXNG has been initialized. Re-enabling 'cap_drop: - ALL' directive for security...")
            # Uncomment the cap_drop line
            modified_content = content.replace("# cap_drop: - ALL  # Temporarily commented out for first run", "cap_drop: - ALL")

            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)

    except Exception as e:
        print(f"Error checking/modifying docker-compose.yml for SearXNG: {e}")

def load_env_file(filepath=".env"):
    """Parse .env file and return dict of values."""
    env = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    env[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"Warning: {filepath} not found")
    return env

def ensure_additional_databases():
    """Check and create any missing databases from POSTGRES_ADDITIONAL_DBS."""
    print("\n" + "-"*60)
    print("Checking for additional databases...")
    print("-"*60)

    # Load .env file
    env = load_env_file()
    additional_dbs = env.get("POSTGRES_ADDITIONAL_DBS", "")
    postgres_user = env.get("POSTGRES_USER", "postgres")

    if not additional_dbs:
        print("No additional databases configured in POSTGRES_ADDITIONAL_DBS")
        return

    # Parse comma-separated list
    requested_dbs = [db.strip() for db in additional_dbs.split(",") if db.strip()]

    print(f"Configured databases: {requested_dbs}")

    # Wait for postgres to be ready
    print("Waiting for PostgreSQL to be ready...")
    max_retries = 30
    for i in range(max_retries):
        result = subprocess.run(
            ["docker", "exec", "postgres", "pg_isready", "-U", postgres_user],
            capture_output=True
        )
        if result.returncode == 0:
            print("PostgreSQL is ready!")
            break
        time.sleep(1)
    else:
        print("Warning: PostgreSQL not ready after 30 seconds, skipping database check")
        return

    # Get list of existing databases
    result = subprocess.run(
        ["docker", "exec", "postgres", "psql", "-U", postgres_user, "-t", "-c",
         "SELECT datname FROM pg_database WHERE datistemplate = false;"],
        capture_output=True, text=True
    )
    existing_dbs = [db.strip() for db in result.stdout.split("\n") if db.strip()]

    # Create missing databases
    created_count = 0
    for db in requested_dbs:
        if db not in existing_dbs:
            print(f"Creating missing database: {db}")
            try:
                subprocess.run(
                    ["docker", "exec", "postgres", "psql", "-U", postgres_user, "-c",
                     f'CREATE DATABASE "{db}";'],
                    check=True, capture_output=True
                )
                # Add extensions
                subprocess.run(
                    ["docker", "exec", "postgres", "psql", "-U", postgres_user, "-d", db, "-c",
                     "CREATE EXTENSION IF NOT EXISTS vector; "
                     "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"; "
                     "CREATE EXTENSION IF NOT EXISTS pg_trgm;"],
                    check=True, capture_output=True
                )
                print(f"  -> Database '{db}' created with AI extensions (vector, uuid-ossp, pg_trgm)")
                created_count += 1
            except subprocess.CalledProcessError as e:
                print(f"  -> Error creating database '{db}': {e}")
        else:
            print(f"Database '{db}' already exists - skipping")

    if created_count > 0:
        print(f"\nCreated {created_count} new database(s)")
    else:
        print("\nAll configured databases already exist")

def main():
    parser = argparse.ArgumentParser(description='Start the local AI services.')
    parser.add_argument('--profile', action='append', dest='profiles',
                      help='Profiles to use for Docker Compose. Can be specified multiple times. '
                           'Options: none, cpu, gpu-nvidia, gpu-amd (for Ollama), '
                           'n8n, flowise, langfuse (for optional services). Default: none')
    parser.add_argument('--environment', choices=['private', 'public'], default='private',
                      help='Environment to use for Docker Compose (default: private)')
    parser.add_argument('--memory-optimized', action='store_true',
                      help='Apply memory limits to reduce RAM usage (recommended for systems with limited memory)')
    args = parser.parse_args()

    # Default to 'none' if no profiles specified
    if not args.profiles:
        args.profiles = ['none']

    # Generate SearXNG secret key and check docker-compose.yml
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng()

    # Stop existing containers
    stop_existing_containers(args.profiles)

    # Start all services
    start_services(args.profiles, args.environment, args.memory_optimized)

    # Ensure all additional databases exist (creates missing ones only)
    ensure_additional_databases()

    print("\n" + "="*60)
    print("Local AI stack started successfully!")
    print(f"Active profiles: {', '.join(args.profiles)}")
    if args.memory_optimized:
        print("Memory optimization: ENABLED (resource limits applied)")
    print("="*60)
    print("\nServices are starting up. Please wait a few moments for PostgreSQL")
    print("to initialize before accessing other services.")
    print("\nAccess services at:")
    if args.environment == "private":
        print("  - n8n: http://localhost:5678")
        print("  - Open WebUI: http://localhost:8080")
        print("  - Flowise: http://localhost:3001")
        print("  - Langfuse: http://localhost:3000")
        print("  - Neo4j Browser: http://localhost:7474")
        print("  - PostgreSQL: localhost:5432")
    else:
        print("  - Services available via Caddy reverse proxy on ports 80/443")
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
