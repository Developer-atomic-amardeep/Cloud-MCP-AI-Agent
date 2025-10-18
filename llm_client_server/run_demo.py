#!/usr/bin/env python3
"""
Demo script to run the hierarchical MCP client with the billing server.

This script helps you run the complete demo by:
1. Starting the billing-cost-management-mcp-server
2. Running the hierarchical client
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def run_billing_server():
    """Run the billing server in the background."""
    print("🚀 Starting AWS Billing and Cost Management MCP Server...")
    
    # Get the path to the billing server script
    billing_server_script = Path(__file__).parent.parent / "run_billing_server.py"
    
    if not billing_server_script.exists():
        print(f"❌ Error: Billing server script not found at {billing_server_script}")
        print("Please make sure you're in the correct directory and the billing server is available.")
        return None
    
    try:
        # Start the billing server
        process = subprocess.Popen([
            sys.executable, str(billing_server_script)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print("✅ Billing server started successfully!")
        print("📡 Server should be available at: http://localhost:8050/sse/")
        print("⏳ Waiting 5 seconds for server to initialize...")
        time.sleep(5)
        
        return process
        
    except Exception as e:
        print(f"❌ Error starting billing server: {e}")
        return None

def run_client():
    """Run the hierarchical client."""
    print("\n🔧 Starting Hierarchical MCP Client...")
    print("=" * 60)
    
    try:
        # Run the client
        client_script = Path(__file__).parent / "client.py"
        result = subprocess.run([sys.executable, str(client_script)], 
                              capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n✅ Client completed successfully!")
        else:
            print(f"\n❌ Client exited with code {result.returncode}")
            
    except Exception as e:
        print(f"❌ Error running client: {e}")

def main():
    """Main function to run the complete demo."""
    print("🎯 HIERARCHICAL MCP CLIENT DEMO")
    print("=" * 60)
    print("This demo will:")
    print("1. Start the AWS Billing and Cost Management MCP Server")
    print("2. Run the Hierarchical MCP Client")
    print("3. Demonstrate the two-step tool selection process")
    print("=" * 60)
    
    # Check if we have the required environment variables
    if not os.getenv("CEBRAS_API_KEY"):
        print("⚠️  Warning: CEBRAS_API_KEY environment variable not set")
        print("Please set your Cerebras API key before running the demo")
        print("You can set it with: export CEBRAS_API_KEY=your_key_here")
        print()
    
    # Start the billing server
    server_process = run_billing_server()
    
    if server_process is None:
        print("❌ Failed to start billing server. Exiting.")
        return
    
    try:
        # Run the client
        run_client()
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
        
    finally:
        # Clean up the server process
        if server_process:
            print("\n🛑 Stopping billing server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
                print("✅ Server stopped successfully")
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing server process...")
                server_process.kill()
                server_process.wait()

if __name__ == "__main__":
    main()
