#!/usr/bin/env python3
"""
Server Selection Module for MCP Client

This module implements the first level of hierarchical selection:
selecting which MCP server to use based on user queries.
"""

import json
import os
from typing import Dict, Any
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv

load_dotenv()


class ServerSelector:
    """
    Handles server selection for MCP client.
    
    First level of the three-level hierarchical selection:
    1. Server Selection (this class)
    2. Tool Group Selection 
    3. Specific Tool Selection
    """
    
    def __init__(self, model: str = "llama-4-scout-17b-16e-instruct"):
        """Initialize the server selector."""
        self.client = Cerebras(api_key=os.getenv("CEBRAS_API_KEY"))
        self.model = model
        
        # Define available MCP servers
        self.servers = {
            "iam": {
                "name": "IAM Management Server",
                "url": "http://localhost:8051/sse/",
                "description": "Manage AWS Identity and Access Management (IAM) resources including users, roles, policies, groups, and access keys",
                "capabilities": [
                    "List, create, delete IAM users",
                    "Manage IAM roles and trust relationships", 
                    "Handle managed and inline policies",
                    "Manage IAM groups and memberships",
                    "Create and delete access keys",
                    "Simulate policy permissions"
                ],
                "expected_tools": ["list_users", "get_user", "create_user", "list_roles", "list_policies", "get_group"],
                "keywords": ["user", "role", "policy", "group", "access key", "permission", "iam", "identity", "access", "management"]
            },
            "billing": {
                "name": "Billing Cost Management Server",
                "url": "http://localhost:8050/sse/",
                "description": "Analyze AWS costs, usage, optimization opportunities, budgets, and savings plans",
                "capabilities": [
                    "Historical cost and usage analysis",
                    "Cost optimization recommendations",
                    "Budget monitoring and alerts",
                    "Savings Plans analysis",
                    "Reserved Instance utilization",
                    "Free tier usage tracking"
                ],
                "expected_tools": ["cost-explorer", "cost-optimization", "budget", "compute-optimizer", "pricing"],
                "keywords": ["cost", "billing", "budget", "savings", "optimization", "usage", "spend", "money", "price", "reserved instance"]
            }
        }
    
    def get_servers_context(self) -> str:
        """
        Generate context string for server selection.
        
        Returns:
            str: Formatted string containing all available servers and their details
        """
        context = "Available MCP Servers:\n\n"
        
        for server_id, server_info in self.servers.items():
            context += f"Server ID: {server_id}\n"
            context += f"Name: {server_info['name']}\n"
            context += f"Description: {server_info['description']}\n"
            context += "Capabilities:\n"
            
            for capability in server_info['capabilities']:
                context += f"  - {capability}\n"
            
            context += f"Keywords: {', '.join(server_info['keywords'])}\n"
            context += "\n"
        
        return context
    
    async def select_server(self, user_query: str) -> Dict[str, Any]:
        """
        Use LLM to select the most appropriate MCP server for the user query.
        
        Args:
            user_query (str): The user's question or request
            
        Returns:
            Dict[str, Any]: JSON response containing the selected server information
        """
        
        servers_context = self.get_servers_context()
        
        system_prompt = """You are a server selector for AWS management tools. Your job is to analyze user queries and select the most appropriate MCP server.

You must respond with ONLY a valid JSON object in this exact format:
{
    "selected_server": "server_id_here",
    "reasoning": "Brief explanation of why this server was selected"
}

Do not include any other text, explanations, or formatting outside the JSON object."""

        user_prompt = f"""User Query: {user_query}

{servers_context}

Based on the user query above, select the most appropriate MCP server. Consider:
- What type of AWS resource or service the user is asking about
- Whether they're asking about identity/access management (IAM) or cost/billing management
- The specific action they want to perform
- The keywords and capabilities that match their request

Guidelines:
- Choose "iam" for queries about users, roles, policies, groups, permissions, access keys, identity management
- Choose "billing" for queries about costs, spending, budgets, optimization, pricing, usage analysis
- If unclear, lean towards the server that best matches the primary intent

Respond with ONLY the JSON object as specified."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent JSON output
                max_tokens=200    # Limit response length to ensure JSON only
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Try to parse the JSON response
            try:
                result = json.loads(response_text)
                
                # Validate that the response has the expected structure
                if "selected_server" not in result:
                    raise ValueError("Missing 'selected_server' in response")
                
                # Validate that the selected server exists
                if result["selected_server"] not in self.servers:
                    raise ValueError(f"Invalid server_id: {result['selected_server']}")
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"Raw response: {response_text}")
                return {
                    "error": "Invalid JSON response",
                    "raw_response": response_text
                }
                
        except Exception as e:
            print(f"❌ Error calling Cerebras API: {e}")
            return {
                "error": f"API call failed: {str(e)}"
            }
    
    def get_server_info(self, server_id: str) -> Dict[str, Any]:
        """Get information about a specific server."""
        if server_id not in self.servers:
            return {"error": f"Server '{server_id}' not found"}
        
        return self.servers[server_id]
    
    def get_server_url(self, server_id: str) -> str:
        """Get the URL for a specific server."""
        if server_id not in self.servers:
            raise ValueError(f"Server '{server_id}' not found")
        
        return self.servers[server_id]["url"]
    
    def get_expected_tools(self, server_id: str) -> list:
        """Get the expected tools for a specific server."""
        if server_id not in self.servers:
            raise ValueError(f"Server '{server_id}' not found")
        
        return self.servers[server_id]["expected_tools"]
