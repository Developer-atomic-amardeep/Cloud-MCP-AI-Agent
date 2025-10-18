#!/usr/bin/env python3
"""
Script to run the iam-mcp-server with AWS credentials loaded from .env
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def main():
    """Start the IAM server with AWS credentials from .env"""
    
    # Try to load .env from multiple locations
    env_locations = [
        Path(__file__).parent / ".env",  # Root directory
        Path(__file__).parent / "llm_client_server" / ".env",  # Client directory
        Path(__file__).parent / "iam-mcp-server" / ".env",  # Server directory
    ]
    
    env_file_found = False
    for env_path in env_locations:
        if env_path.exists():
            print(f"✅ Loading environment variables from: {env_path}")
            load_dotenv(env_path, override=True)
            env_file_found = True
            break
    
    if not env_file_found:
        print("⚠️  No .env file found. Please create one with your AWS credentials.")
        print("   Expected locations:")
        for loc in env_locations:
            print(f"   - {loc}")
        print("\n   Required variables:")
        print("   - AWS_ACCESS_KEY_ID")
        print("   - AWS_SECRET_ACCESS_KEY")
        print("   - AWS_REGION (e.g., us-east-1)")
        sys.exit(1)
    
    # Check if AWS credentials are set
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    if not aws_access_key or not aws_secret_key:
        print("❌ AWS credentials not found in .env file!")
        print("   Please ensure your .env file contains:")
        print("   - AWS_ACCESS_KEY_ID=your_access_key")
        print("   - AWS_SECRET_ACCESS_KEY=your_secret_key")
        print("   - AWS_REGION=us-east-1")
        sys.exit(1)
    
    print("🔐 AWS Configuration:")
    print(f"   Region: {aws_region}")
    print(f"   Access Key ID: {aws_access_key[:10]}...{aws_access_key[-4:] if len(aws_access_key) > 14 else ''}")
    print(f"   Secret Access Key: {'*' * 20}")
    
    # Set up the environment for the subprocess
    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"] = aws_access_key
    env["AWS_SECRET_ACCESS_KEY"] = aws_secret_key
    env["AWS_REGION"] = aws_region
    
    # Add session token if available
    if os.getenv("AWS_SESSION_TOKEN"):
        env["AWS_SESSION_TOKEN"] = os.getenv("AWS_SESSION_TOKEN")
        print("   Session Token: Set")
    
    print("\n🚀 Starting iam-mcp-server...")
    print("   Server will be available at: http://localhost:8051/sse/")
    print("   Press Ctrl+C to stop the server\n")
    
    # Path to the server directory and script
    server_dir = Path(__file__).parent / "iam-mcp-server"
    server_script = server_dir / "awslabs" / "iam_mcp_server" / "server.py"
    
    if not server_script.exists():
        print(f"❌ Server script not found at: {server_script}")
        sys.exit(1)
    
    # Add the iam-mcp-server directory to PYTHONPATH so it can find the awslabs package
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{server_dir}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = str(server_dir)
    
    # Run the server with the environment variables
    try:
        subprocess.run(
            [sys.executable, str(server_script)],
            env=env,
            check=True
        )
    except KeyboardInterrupt:
        print("\n\n✋ Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Server exited with error code {e.returncode}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

