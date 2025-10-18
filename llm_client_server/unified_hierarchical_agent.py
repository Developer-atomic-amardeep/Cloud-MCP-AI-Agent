#!/usr/bin/env python3
"""
Unified Hierarchical Agent for Tool Group and Tool Selection

This module implements the second and third levels of hierarchical selection:
2. Tool Group Selection (within selected server)
3. Specific Tool Selection (within selected group)

Combines tool groups from both IAM and Billing servers.
"""

import json
import os
from typing import Dict, Any
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv

load_dotenv()


class UnifiedHierarchicalAgent:
    """
    Unified hierarchical agent that handles tool group and tool selection
    for both IAM and Billing MCP servers.
    
    Second and third levels of the three-level hierarchical selection:
    1. Server Selection (handled by ServerSelector)
    2. Tool Group Selection (this class)
    3. Specific Tool Selection (this class)
    """
    
    def __init__(self, model: str = "llama-4-scout-17b-16e-instruct"):
        """Initialize the unified hierarchical agent."""
        self.client = Cerebras(api_key=os.getenv("CEBRAS_API_KEY"))
        self.model = model
        
        # Define tool groups for both servers
        self.tool_groups = {
            "iam": {
                "user_management": {
                    "name": "User Management",
                    "description": "Tools for managing IAM users, including creation, listing, deletion, and retrieving user details",
                    "tools": {
                        "list_users": "List IAM users with optional path filtering",
                        "get_user": "Get detailed information about a specific user including policies and access keys",
                        "create_user": "Create a new IAM user with optional permissions boundary",
                        "delete_user": "Delete an IAM user with optional force cleanup"
                    }
                },
                "role_management": {
                    "name": "Role Management",
                    "description": "Tools for managing IAM roles and trust relationships",
                    "tools": {
                        "list_roles": "List IAM roles with optional path filtering",
                        "create_role": "Create a new IAM role with assume role policy document"
                    }
                },
                "policy_management": {
                    "name": "Policy Management",
                    "description": "Tools for managing managed IAM policies and policy documents",
                    "tools": {
                        "list_policies": "List managed IAM policies with scope filtering",
                        "get_managed_policy_document": "Retrieve policy document for a managed policy",
                        "attach_user_policy": "Attach a managed policy to a user",
                        "detach_user_policy": "Detach a managed policy from a user",
                        "simulate_principal_policy": "Simulate policy evaluation to test permissions"
                    }
                },
                "group_management": {
                    "name": "Group Management",
                    "description": "Tools for managing IAM groups, members, and group policies",
                    "tools": {
                        "list_groups": "List IAM groups with optional path filtering",
                        "get_group": "Get detailed information about a group including members and policies",
                        "create_group": "Create a new IAM group",
                        "delete_group": "Delete an IAM group with optional force cleanup",
                        "add_user_to_group": "Add a user to an IAM group",
                        "remove_user_from_group": "Remove a user from an IAM group",
                        "attach_group_policy": "Attach a managed policy to a group",
                        "detach_group_policy": "Detach a managed policy from a group"
                    }
                },
                "access_key_management": {
                    "name": "Access Key Management",
                    "description": "Tools for managing IAM user access keys for programmatic access",
                    "tools": {
                        "create_access_key": "Create a new access key for a user",
                        "delete_access_key": "Delete an access key for a user"
                    }
                },
                "inline_policy_management": {
                    "name": "Inline Policy Management",
                    "description": "Tools for managing inline policies attached directly to users and roles",
                    "tools": {
                        "put_user_policy": "Create or update an inline policy for a user",
                        "get_user_policy": "Retrieve an inline policy document for a user",
                        "delete_user_policy": "Delete an inline policy from a user",
                        "list_user_policies": "List all inline policies for a user",
                        "put_role_policy": "Create or update an inline policy for a role",
                        "get_role_policy": "Retrieve an inline policy document for a role",
                        "delete_role_policy": "Delete an inline policy from a role",
                        "list_role_policies": "List all inline policies for a role"
                    }
                }
            },
            "billing": {
                "core_cost_analysis": {
                    "name": "Core Cost Analysis",
                    "description": "Tools for analyzing historical costs, comparing periods, and detecting anomalies",
                    "tools": {
                        "cost-explorer": "Historical cost and usage data with flexible filtering and forecasting",
                        "cost-comparison": "Compare costs between time periods with detailed breakdown",
                        "cost-anomaly": "Identify unusual spending patterns and their root causes"
                    }
                },
                "optimization_recommendations": {
                    "name": "Optimization & Recommendations", 
                    "description": "Tools for cost optimization and performance recommendations",
                    "tools": {
                        "cost-optimization": "Cost optimization recommendations from Cost Optimization Hub",
                        "compute-optimizer": "Performance optimization recommendations for compute resources",
                        "rec-details": "Enhanced cost optimization recommendation details",
                        "ri-performance": "Reserved Instance coverage and utilization analysis"
                    }
                },
                "savings_plans_pricing": {
                    "name": "Savings Plans & Pricing",
                    "description": "Tools for analyzing savings plans and AWS pricing information",
                    "tools": {
                        "sp-performance": "Savings Plans coverage, utilization and purchase recommendations",
                        "pricing": "AWS service pricing information and product details"
                    }
                },
                "monitoring_usage": {
                    "name": "Monitoring & Usage",
                    "description": "Tools for monitoring budgets, free tier usage, and storage metrics",
                    "tools": {
                        "budget": "AWS budget information and status monitoring",
                        "free-tier-usage": "AWS Free Tier usage monitoring to avoid unexpected charges",
                        "storage-lens": "S3 Storage Lens metrics analysis with SQL queries"
                    }
                },
                "advanced_query": {
                    "name": "Advanced Query",
                    "description": "Tools for custom SQL analysis and data exploration",
                    "tools": {
                        "session-sql": "Execute SQL queries on session database for custom analysis"
                    }
                },
                "specialized_analysis": {
                    "name": "Specialized Analysis",
                    "description": "Guided analysis prompts for specific optimization scenarios",
                    "tools": {
                        "savings_plans_analysis": "Guided Savings Plans purchase analysis with usage patterns",
                        "graviton_analysis": "EC2 Graviton migration opportunity identification"
                    }
                }
            }
        }
    
    def get_tool_groups_context(self, server_id: str) -> str:
        """
        Generate context string for tool groups of a specific server.
        
        Args:
            server_id (str): The server ID ("iam" or "billing")
            
        Returns:
            str: Formatted string containing tool groups for the server
        """
        if server_id not in self.tool_groups:
            return f"Error: Server '{server_id}' not found"
        
        context = f"Available Tool Groups for {server_id.upper()} Server:\n\n"
        
        for group_id, group_info in self.tool_groups[server_id].items():
            context += f"Group ID: {group_id}\n"
            context += f"Name: {group_info['name']}\n"
            context += f"Description: {group_info['description']}\n"
            context += "Tools:\n"
            
            for tool_name, tool_description in group_info['tools'].items():
                context += f"  - {tool_name}: {tool_description}\n"
            
            context += "\n"
        
        return context
    
    async def select_tool_group(self, user_query: str, server_id: str) -> Dict[str, Any]:
        """
        Use LLM to select the most appropriate tool group for the user query within a specific server.
        
        Args:
            user_query (str): The user's question or request
            server_id (str): The selected server ID ("iam" or "billing")
            
        Returns:
            Dict[str, Any]: JSON response containing the selected group information
        """
        
        if server_id not in self.tool_groups:
            return {
                "error": f"Invalid server_id: {server_id}"
            }
        
        tool_groups_context = self.get_tool_groups_context(server_id)
        server_type = "AWS IAM management" if server_id == "iam" else "AWS cost management"
        
        system_prompt = f"""You are a tool group selector for {server_type}. Your job is to analyze user queries and select the most appropriate tool group.

You must respond with ONLY a valid JSON object in this exact format:
{{
    "selected_group_id": "group_id_here",
    "reasoning": "Brief explanation of why this group was selected"
}}

Do not include any other text, explanations, or formatting outside the JSON object."""

        if server_id == "iam":
            guidelines = """Consider:
- What type of IAM resource the user is asking about (users, roles, groups, policies, access keys)
- Whether they want to manage inline policies specifically
- The specific action they want to perform"""
        else:
            guidelines = """Consider:
- What type of analysis the user is requesting
- Whether they need historical data, optimization recommendations, monitoring, etc.
- The specific AWS services or cost aspects they're interested in"""

        user_prompt = f"""User Query: {user_query}

{tool_groups_context}

Based on the user query above, select the most appropriate tool group. {guidelines}

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
                if "selected_group_id" not in result:
                    raise ValueError("Missing 'selected_group_id' in response")
                
                # Validate that the selected group exists in the server
                if result["selected_group_id"] not in self.tool_groups[server_id]:
                    raise ValueError(f"Invalid group_id: {result['selected_group_id']}")
                
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
    
    def get_tools_context_for_group(self, server_id: str, group_id: str) -> str:
        """
        Generate context string for tools in a specific group.
        
        Args:
            server_id (str): The server ID ("iam" or "billing")
            group_id (str): The ID of the tool group
            
        Returns:
            str: Formatted string containing tools in the group
        """
        if server_id not in self.tool_groups:
            return f"Error: Server '{server_id}' not found"
        
        if group_id not in self.tool_groups[server_id]:
            return f"Error: Group '{group_id}' not found in server '{server_id}'"
        
        group = self.tool_groups[server_id][group_id]
        context = f"Available Tools in {group['name']} Group:\n\n"
        context += f"Description: {group['description']}\n\n"
        context += "Tools:\n"
        
        for tool_name, tool_description in group['tools'].items():
            context += f"  - {tool_name}: {tool_description}\n"
        
        return context
    
    async def select_specific_tool(self, user_query: str, server_id: str, group_id: str) -> Dict[str, Any]:
        """
        Use LLM to select the most appropriate specific tool from the chosen group.
        
        Args:
            user_query (str): The original user's question or request
            server_id (str): The selected server ID ("iam" or "billing")
            group_id (str): The selected tool group ID
            
        Returns:
            Dict[str, Any]: JSON response containing the selected tool information
        """
        
        if server_id not in self.tool_groups:
            return {
                "error": f"Invalid server_id: {server_id}"
            }
        
        if group_id not in self.tool_groups[server_id]:
            return {
                "error": f"Invalid group_id: {group_id}"
            }
        
        tools_context = self.get_tools_context_for_group(server_id, group_id)
        group_name = self.tool_groups[server_id][group_id]['name']
        server_type = "AWS IAM management" if server_id == "iam" else "AWS cost management"
        
        system_prompt = f"""You are a tool selector for {server_type}. Your job is to analyze user queries and select the most appropriate specific tool from the {group_name} group.

You must respond with ONLY a valid JSON object in this exact format:
{{
    "selected_tool": "tool_name_here",
    "reasoning": "Brief explanation of why this specific tool was selected"
}}

Do not include any other text, explanations, or formatting outside the JSON object."""

        user_prompt = f"""Original User Query: {user_query}

{tools_context}

Based on the original user query above, select the most appropriate specific tool from the {group_name} group. Consider:
- What specific action the user wants to perform
- Which tool best matches their exact needs
- The specific functionality each tool provides

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
                if "selected_tool" not in result:
                    raise ValueError("Missing 'selected_tool' in response")
                
                # Validate that the selected tool exists in the group
                available_tools = list(self.tool_groups[server_id][group_id]['tools'].keys())
                if result["selected_tool"] not in available_tools:
                    raise ValueError(f"Invalid tool: {result['selected_tool']}. Available tools: {available_tools}")
                
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
    
    def get_group_info(self, server_id: str, group_id: str) -> Dict[str, Any]:
        """Get information about a specific tool group."""
        if server_id not in self.tool_groups:
            return {"error": f"Server '{server_id}' not found"}
        
        if group_id not in self.tool_groups[server_id]:
            return {"error": f"Group '{group_id}' not found in server '{server_id}'"}
        
        return self.tool_groups[server_id][group_id]
    
    def get_tool_description(self, server_id: str, group_id: str, tool_name: str) -> str:
        """Get description of a specific tool."""
        if server_id not in self.tool_groups:
            return f"Server '{server_id}' not found"
        
        if group_id not in self.tool_groups[server_id]:
            return f"Group '{group_id}' not found in server '{server_id}'"
        
        tools = self.tool_groups[server_id][group_id]['tools']
        if tool_name not in tools:
            return f"Tool '{tool_name}' not found in group '{group_id}'"
        
        return tools[tool_name]
    
    async def hierarchical_tool_selection(self, user_query: str, server_id: str) -> Dict[str, Any]:
        """
        Perform hierarchical tool selection within a specific server: first select group, then select specific tool.
        
        Args:
            user_query (str): The user's question or request
            server_id (str): The selected server ID ("iam" or "billing")
            
        Returns:
            Dict[str, Any]: Complete selection result with group and tool information
        """
        
        # Step 1: Select tool group
        group_result = await self.select_tool_group(user_query, server_id)
        
        if "error" in group_result:
            return {
                "error": f"Group selection failed: {group_result['error']}",
                "stage": "group_selection",
                "server_id": server_id
            }
        
        selected_group_id = group_result["selected_group_id"]
        group_reasoning = group_result.get("reasoning", "No reasoning provided")
        
        # Step 2: Select specific tool from the group
        tool_result = await self.select_specific_tool(user_query, server_id, selected_group_id)
        
        if "error" in tool_result:
            return {
                "error": f"Tool selection failed: {tool_result['error']}",
                "stage": "tool_selection",
                "server_id": server_id,
                "selected_group": {
                    "group_id": selected_group_id,
                    "group_name": self.tool_groups[server_id][selected_group_id]['name'],
                    "reasoning": group_reasoning
                }
            }
        
        selected_tool = tool_result["selected_tool"]
        tool_reasoning = tool_result.get("reasoning", "No reasoning provided")
        
        return {
            "success": True,
            "server_id": server_id,
            "selected_group": {
                "group_id": selected_group_id,
                "group_name": self.tool_groups[server_id][selected_group_id]['name'],
                "reasoning": group_reasoning
            },
            "selected_tool": {
                "tool_name": selected_tool,
                "tool_description": self.tool_groups[server_id][selected_group_id]['tools'][selected_tool],
                "reasoning": tool_reasoning
            },
            "user_query": user_query
        }
