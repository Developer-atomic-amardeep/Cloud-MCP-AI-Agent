# Cloud MCP AI Agent

A comprehensive Model Context Protocol (MCP) system that provides AI assistants with access to AWS services through specialized MCP servers. This project includes both MCP servers for AWS services and an intelligent client that can automatically route queries to the appropriate server.

## 🏗️ Architecture

This project consists of three main components:

1. **AWS IAM MCP Server** - Manages AWS Identity and Access Management operations
2. **AWS Billing & Cost Management MCP Server** - Handles AWS cost analysis and optimization
3. **Intelligent MCP Client** - Routes queries to appropriate servers using hierarchical selection

## 🚀 Quick Start

### Prerequisites

1. **Python 3.10+** - Install using [uv](https://docs.astral.sh/uv/getting-started/installation/):
   ```bash
   uv python install 3.10
   ```

2. **AWS Credentials** - Configure using one of these methods:
   ```bash
   # Option 1: AWS Profile (recommended)
   export AWS_PROFILE=your-profile-name
   
   # Option 2: Environment Variables
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   export AWS_REGION=us-east-1
   ```

3. **Cerebras API Key** - For the intelligent client:
   ```bash
   export CEBRAS_API_KEY=your-cerebras-api-key
   ```

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd Cloud-MCP-AI-Agent

# Install dependencies
uv sync
```

### Environment Setup

Create `.env` files in the appropriate directories:

```bash
# Root directory .env (for client)
echo "CEBRAS_API_KEY=your-cerebras-api-key" > .env

# IAM server .env
echo "AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1" > iam-mcp-server/.env

# Billing server .env
echo "AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1" > billing-cost-management-mcp-server/.env
```

## 🖥️ Running the Servers

### IAM MCP Server

```bash
# Start the IAM server
python run_iam_server.py

# Server will be available at: http://localhost:8051/sse/
```

**Features:**
- User, role, group, and policy management
- Access key management
- Policy simulation and validation
- Inline policy CRUD operations
- Security best practices enforcement

### Billing & Cost Management MCP Server

```bash
# Start the billing server
python run_billing_server.py

# Server will be available at: http://localhost:8050/sse/
```

**Features:**
- Cost Explorer insights and analysis
- Budget monitoring and alerts
- Cost optimization recommendations
- Reserved Instance and Savings Plans analysis
- Free Tier usage monitoring
- S3 Storage Lens analytics
- Cost anomaly detection

## 🤖 Using the Intelligent Client

The intelligent client automatically routes your queries to the appropriate MCP server using a three-level hierarchical selection system:

1. **Server Selection** - Chooses between IAM or Billing server
2. **Tool Group Selection** - Selects the appropriate tool category
3. **Tool Selection** - Picks the specific tool to execute

### Running the Client

```bash
cd llm_client_server
python client.py
```

### Client Components

- **`client.py`** - Main client with intelligent routing
- **`server_selector.py`** - Handles server selection logic
- **`unified_hierarchical_agent.py`** - Manages tool group and tool selection
- **`hierarchical_agent.py`** - Legacy hierarchical agent (backward compatibility)
- **`server.py`** - Local server implementation

### Example Usage

```python
from llm_client_server.client import MCPCerebrasClient

# Initialize client
client = MCPCerebrasClient()

# Connect to servers
await client.connect_to_server("http://localhost:8051/sse/")  # IAM
await client.connect_to_server("http://localhost:8050/sse/")  # Billing

# Query examples
await client.query("List all IAM users in my account")
await client.query("Show me my AWS costs for the last month")
await client.query("What are my cost optimization opportunities?")
```

## 📁 Project Structure

```
Cloud-MCP-AI-Agent/
├── README.md                          # This file
├── pyproject.toml                     # Project configuration
├── run_iam_server.py                  # IAM server launcher
├── run_billing_server.py              # Billing server launcher
├── .gitignore                         # Git ignore rules
│
├── iam-mcp-server/                    # AWS IAM MCP Server
│   ├── README.md                      # IAM server documentation
│   ├── pyproject.toml                 # IAM server config
│   ├── awslabs/iam_mcp_server/        # Server implementation
│   └── tests/                         # IAM server tests
│
├── billing-cost-management-mcp-server/ # AWS Billing MCP Server
│   ├── README.md                      # Billing server documentation
│   ├── pyproject.toml                 # Billing server config
│   ├── awslabs/billing_cost_management_mcp_server/ # Server implementation
│   └── tests/                         # Billing server tests
│
└── llm_client_server/                 # Intelligent MCP Client
    ├── client.py                      # Main client implementation
    ├── server_selector.py             # Server selection logic
    ├── unified_hierarchical_agent.py  # Tool selection logic
    ├── hierarchical_agent.py          # Legacy agent
    ├── server.py                      # Local server
    └── data/                          # Client data files
```

## 🔧 Configuration

### Server Configuration

Both MCP servers support various configuration options:

**IAM Server:**
- `--read-only` - Run in read-only mode (no modifications)
- `--region` - AWS region (default: us-east-1)

**Billing Server:**
- `--region` - AWS region (default: us-east-1)
- Custom SQL session management for complex queries

### Client Configuration

The client can be configured through environment variables:

```bash
# Cerebras API settings
CEBRAS_API_KEY=your-api-key

# Server endpoints (if different from defaults)
IAM_SERVER_URL=http://localhost:8051/sse/
BILLING_SERVER_URL=http://localhost:8050/sse/
```

## 🛡️ Security

### Best Practices

1. **Environment Variables** - All sensitive data is loaded from environment variables
2. **AWS Credentials** - Use IAM roles or profiles instead of hardcoded keys
3. **Read-Only Mode** - Run servers in read-only mode for safety
4. **Least Privilege** - Grant minimal required AWS permissions

### Required AWS Permissions

**For IAM Server:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:List*",
                "iam:Get*",
                "iam:Create*",
                "iam:Delete*",
                "iam:Attach*",
                "iam:Detach*",
                "iam:Put*",
                "iam:Simulate*"
            ],
            "Resource": "*"
        }
    ]
}
```

**For Billing Server:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:*",
                "budgets:View*",
                "compute-optimizer:Get*",
                "compute-optimizer:Describe*",
                "cost-optimization-hub:Get*",
                "cost-optimization-hub:List*",
                "s3:GetStorageLensConfiguration*",
                "freetier:GetFreeTierUsage"
            ],
            "Resource": "*"
        }
    ]
}
```

## 🧪 Testing

### Running Tests

```bash
# Test IAM server
cd iam-mcp-server
python -m pytest tests/

# Test Billing server
cd billing-cost-management-mcp-server
python -m pytest tests/

# Test client components
cd llm_client_server
python -m pytest
```

### Manual Testing

```bash
# Test server connectivity
curl http://localhost:8051/sse/  # IAM server
curl http://localhost:8050/sse/  # Billing server
```

## 📚 Documentation

- [IAM Server Documentation](iam-mcp-server/README.md)
- [Billing Server Documentation](billing-cost-management-mcp-server/README.md)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the individual server directories for specific license files.

## 🆘 Troubleshooting

### Common Issues

1. **Server won't start:**
   - Check AWS credentials are configured
   - Verify ports 8050 and 8051 are available
   - Check Python version (3.10+ required)

2. **Client connection fails:**
   - Ensure servers are running
   - Verify CEBRAS_API_KEY is set
   - Check server URLs are correct

3. **AWS permission errors:**
   - Verify IAM permissions match requirements
   - Check AWS region configuration
   - Ensure credentials have necessary access

### Debug Mode

Enable debug logging:

```bash
export MCP_DEBUG=1
python run_iam_server.py
```

## 🔄 Updates

To update the project:

```bash
git pull origin main
uv sync  # Update dependencies
```

---

**Note:** This project provides powerful AWS management capabilities. Always test in a development environment before using in production, and follow AWS security best practices.
