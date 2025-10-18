#!/usr/bin/env python3
"""
Hierarchical Structured Agent for Tool Group Selection

This module implements a hierarchical approach to solve context length overflow issues
by first using an LLM to select the appropriate tool group, then using specific tools
from that group to answer the user's query.

The system uses llama-4-scout-17b-16e-instruct to analyze user queries and select
the most appropriate tool group from the billing-cost-management-mcp-server.
"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv

load_dotenv()


class HierarchicalAgent:
    """
    Hierarchical agent that first selects tool groups, then uses specific tools.
    
    This approach helps solve context length issues by:
    1. First LLM call: Select appropriate tool group based on user query
    2. Second LLM call: Use only tools from selected group to answer query
    """
    
    def __init__(self, model: str = "llama-4-scout-17b-16e-instruct"):
        """Initialize the hierarchical agent."""
        self.client = Cerebras(api_key=os.getenv("CEBRAS_API_KEY"))
        self.model = model
        
        # Define the grouped tool structure from billing-cost-management-mcp-server
        self.tool_groups = {
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
    
    def get_tool_groups_context(self) -> str:
        """
        Generate the context string for tool groups that will be sent to the LLM.
        
        Returns:
            str: Formatted string containing all tool groups and their details
        """
        context = "Available Tool Groups:\n\n"
        
        for group_id, group_info in self.tool_groups.items():
            context += f"Group ID: {group_id}\n"
            context += f"Name: {group_info['name']}\n"
            context += f"Description: {group_info['description']}\n"
            context += "Tools:\n"
            
            for tool_name, tool_description in group_info['tools'].items():
                context += f"  - {tool_name}: {tool_description}\n"
            
            context += "\n"
        
        return context
    
    async def select_tool_group(self, user_query: str) -> Dict[str, Any]:
        """
        Use LLM to select the most appropriate tool group for the user query.
        
        Args:
            user_query (str): The user's question or request
            
        Returns:
            Dict[str, Any]: JSON response containing the selected group information
        """
        
        tool_groups_context = self.get_tool_groups_context()
        
        system_prompt = """You are a tool group selector for AWS cost management. Your job is to analyze user queries and select the most appropriate tool group.

You must respond with ONLY a valid JSON object in this exact format:
{
    "selected_group_id": "group_id_here",
    "reasoning": "Brief explanation of why this group was selected"
}

Do not include any other text, explanations, or formatting outside the JSON object."""

        user_prompt = f"""User Query: {user_query}

{tool_groups_context}

Based on the user query above, select the most appropriate tool group. Consider:
- What type of analysis the user is requesting
- Whether they need historical data, optimization recommendations, monitoring, etc.
- The specific AWS services or cost aspects they're interested in

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
                
                # Validate that the selected group exists
                if result["selected_group_id"] not in self.tool_groups:
                    raise ValueError(f"Invalid group_id: {result['selected_group_id']}")
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
                print(f"Raw response: {response_text}")
                return {
                    "error": "Invalid JSON response",
                    "raw_response": response_text
                }
                
        except Exception as e:
            print(f"Error calling Cerebras API: {e}")
            return {
                "error": f"API call failed: {str(e)}"
            }
    
    def get_tools_context_for_group(self, group_id: str) -> str:
        """
        Generate the context string for tools in a specific group.
        
        Args:
            group_id (str): The ID of the tool group
            
        Returns:
            str: Formatted string containing tools in the group
        """
        if group_id not in self.tool_groups:
            return f"Error: Group '{group_id}' not found"
        
        group = self.tool_groups[group_id]
        context = f"Available Tools in {group['name']} Group:\n\n"
        context += f"Description: {group['description']}\n\n"
        context += "Tools:\n"
        
        for tool_name, tool_description in group['tools'].items():
            context += f"- {tool_name}: {tool_description}\n"
        
        return context
    
    async def select_specific_tool(self, user_query: str, group_id: str) -> Dict[str, Any]:
        """
        Use LLM to select the most appropriate specific tool from the chosen group.
        
        Args:
            user_query (str): The original user's question or request
            group_id (str): The selected tool group ID
            
        Returns:
            Dict[str, Any]: JSON response containing the selected tool information
        """
        
        if group_id not in self.tool_groups:
            return {
                "error": f"Invalid group_id: {group_id}"
            }
        
        tools_context = self.get_tools_context_for_group(group_id)
        group_name = self.tool_groups[group_id]['name']
        
        system_prompt = f"""You are a tool selector for AWS cost management. Your job is to analyze user queries and select the most appropriate specific tool from the {group_name} group.

You must respond with ONLY a valid JSON object in this exact format:
{{
    "selected_tool": "tool_name_here",
    "reasoning": "Brief explanation of why this specific tool was selected"
}}

Do not include any other text, explanations, or formatting outside the JSON object."""

        user_prompt = f"""Original User Query: {user_query}

{tools_context}

Based on the original user query above, select the most appropriate specific tool from the {group_name} group. Consider:
- What specific action or analysis the user is requesting
- Which tool best matches their exact needs
- The specific functionality each tool provides
- The user's intent and desired outcome

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
                available_tools = list(self.tool_groups[group_id]['tools'].keys())
                if result["selected_tool"] not in available_tools:
                    raise ValueError(f"Invalid tool: {result['selected_tool']}. Available tools: {available_tools}")
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
                print(f"Raw response: {response_text}")
                return {
                    "error": "Invalid JSON response",
                    "raw_response": response_text
                }
                
        except Exception as e:
            print(f"Error calling Cerebras API: {e}")
            return {
                "error": f"API call failed: {str(e)}"
            }
    
    async def hierarchical_tool_selection(self, user_query: str) -> Dict[str, Any]:
        """
        Perform hierarchical tool selection: first select group, then select specific tool.
        
        Args:
            user_query (str): The user's question or request
            
        Returns:
            Dict[str, Any]: Complete selection result with group and tool information
        """
        
        # Step 1: Select tool group
        group_result = await self.select_tool_group(user_query)
        
        if "error" in group_result:
            return {
                "error": f"Group selection failed: {group_result['error']}",
                "stage": "group_selection"
            }
        
        selected_group_id = group_result["selected_group_id"]
        group_reasoning = group_result.get("reasoning", "No reasoning provided")
        
        # Step 2: Select specific tool from the group
        tool_result = await self.select_specific_tool(user_query, selected_group_id)
        
        if "error" in tool_result:
            return {
                "error": f"Tool selection failed: {tool_result['error']}",
                "stage": "tool_selection",
                "selected_group": {
                    "group_id": selected_group_id,
                    "group_name": self.tool_groups[selected_group_id]['name'],
                    "reasoning": group_reasoning
                }
            }
        
        selected_tool = tool_result["selected_tool"]
        tool_reasoning = tool_result.get("reasoning", "No reasoning provided")
        
        return {
            "success": True,
            "selected_group": {
                "group_id": selected_group_id,
                "group_name": self.tool_groups[selected_group_id]['name'],
                "reasoning": group_reasoning
            },
            "selected_tool": {
                "tool_name": selected_tool,
                "tool_description": self.tool_groups[selected_group_id]['tools'][selected_tool],
                "reasoning": tool_reasoning
            },
            "user_query": user_query
        }
    
