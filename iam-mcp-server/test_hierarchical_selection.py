#!/usr/bin/env python3
"""
Test file for hierarchical tool selection for IAM MCP Server.

This script tests whether the LLM can correctly select tool groups
based on user queries, without actually connecting to the MCP server.
"""

import asyncio
import json
import os
from typing import Dict, List, Any
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv

load_dotenv()


class IAMHierarchicalAgent:
    """
    Hierarchical agent for IAM tool group selection.
    
    This agent helps solve context length issues by first selecting
    the appropriate tool group before using specific tools.
    """
    
    def __init__(self, model: str = "llama-4-scout-17b-16e-instruct"):
        """Initialize the hierarchical agent."""
        self.client = Cerebras(api_key=os.getenv("CEBRAS_API_KEY"))
        self.model = model
        
        # Define the grouped tool structure for IAM MCP Server
        # Based on the 29 tools we found in the server
        self.tool_groups = {
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
        
        system_prompt = """You are a tool group selector for AWS IAM management. Your job is to analyze user queries and select the most appropriate tool group.

You must respond with ONLY a valid JSON object in this exact format:
{
    "selected_group_id": "group_id_here",
    "reasoning": "Brief explanation of why this group was selected"
}

Do not include any other text, explanations, or formatting outside the JSON object."""

        user_prompt = f"""User Query: {user_query}

{tool_groups_context}

Based on the user query above, select the most appropriate tool group. Consider:
- What type of IAM resource the user is asking about (users, roles, groups, policies, access keys)
- Whether they want to manage inline policies specifically
- The specific action they want to perform

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
    
    def get_group_info(self, group_id: str) -> Dict[str, Any]:
        """Get information about a specific tool group."""
        if group_id not in self.tool_groups:
            return {"error": f"Group '{group_id}' not found"}
        
        return self.tool_groups[group_id]
    
    def get_tools_context_for_group(self, group_id: str) -> str:
        """
        Generate context string for tools in a specific group.
        
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
            context += f"  - {tool_name}: {tool_description}\n"
        
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
        
        system_prompt = f"""You are a tool selector for AWS IAM management. Your job is to analyze user queries and select the most appropriate specific tool from the {group_name} group.

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
                available_tools = list(self.tool_groups[group_id]['tools'].keys())
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


async def test_hierarchical_tool_selection():
    """Test the complete hierarchical tool selection: group selection + specific tool selection."""
    
    print("=" * 80)
    print("IAM HIERARCHICAL TOOL SELECTION TEST")
    print("Testing both Group Selection and Specific Tool Selection")
    print("=" * 80)
    print()
    
    # Check for API key
    api_key = os.getenv("CEBRAS_API_KEY")
    if not api_key:
        print("❌ ERROR: CEBRAS_API_KEY not found in environment variables!")
        print("Please create a .env file with your Cerebras API key:")
        print("   CEBRAS_API_KEY=your_api_key_here")
        return
    
    print(f"✅ Cerebras API Key found: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    agent = IAMHierarchicalAgent()
    
    # Test queries with expected group AND expected tool
    test_queries = [
        {
            "query": "List all IAM users in my AWS account",
            "expected_group": "user_management",
            "expected_tool": "list_users"
        },
        {
            "query": "Create a new IAM user named 'john-doe'",
            "expected_group": "user_management",
            "expected_tool": "create_user"
        },
        {
            "query": "Get detailed information about user 'admin'",
            "expected_group": "user_management",
            "expected_tool": "get_user"
        },
        {
            "query": "Delete IAM user 'old-user'",
            "expected_group": "user_management",
            "expected_tool": "delete_user"
        },
        {
            "query": "Show me all IAM roles",
            "expected_group": "role_management",
            "expected_tool": "list_roles"
        },
        {
            "query": "Create a new role for Lambda execution",
            "expected_group": "role_management",
            "expected_tool": "create_role"
        },
        {
            "query": "I need to attach a policy to a user",
            "expected_group": "policy_management",
            "expected_tool": "attach_user_policy"
        },
        {
            "query": "Show me the policy document for a managed policy",
            "expected_group": "policy_management",
            "expected_tool": "get_managed_policy_document"
        },
        {
            "query": "Test if a user has permission to access S3",
            "expected_group": "policy_management",
            "expected_tool": "simulate_principal_policy"
        },
        {
            "query": "Create an access key for user 'api-user'",
            "expected_group": "access_key_management",
            "expected_tool": "create_access_key"
        },
        {
            "query": "Delete the access key AKIAIOSFODNN7EXAMPLE",
            "expected_group": "access_key_management",
            "expected_tool": "delete_access_key"
        },
        {
            "query": "Add user 'john' to the 'developers' group",
            "expected_group": "group_management",
            "expected_tool": "add_user_to_group"
        },
        {
            "query": "List all groups in my account",
            "expected_group": "group_management",
            "expected_tool": "list_groups"
        },
        {
            "query": "Get details about the 'admins' group",
            "expected_group": "group_management",
            "expected_tool": "get_group"
        },
        {
            "query": "Create an inline policy for a user",
            "expected_group": "inline_policy_management",
            "expected_tool": "put_user_policy"
        },
        {
            "query": "Get the inline policy document for a role",
            "expected_group": "inline_policy_management",
            "expected_tool": "get_role_policy"
        },
        {
            "query": "List all inline policies attached to user 'developer'",
            "expected_group": "inline_policy_management",
            "expected_tool": "list_user_policies"
        },
        {
            "query": "Delete the inline policy from a role",
            "expected_group": "inline_policy_management",
            "expected_tool": "delete_role_policy"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}/{len(test_queries)}")
        print(f"{'=' * 80}")
        print(f"Query: {test['query']}")
        print(f"Expected Group: {test['expected_group']}")
        print(f"Expected Tool: {test['expected_tool']}")
        print()
        
        # STEP 1: Select tool group
        print("🔍 Step 1: Selecting tool group...")
        group_result = await agent.select_tool_group(test['query'])
        
        if "error" in group_result:
            print(f"❌ STEP 1 FAILED: {group_result['error']}")
            if "raw_response" in group_result:
                print(f"Raw Response: {group_result['raw_response']}")
            results.append({
                "test_number": i,
                "query": test['query'],
                "expected_group": test['expected_group'],
                "actual_group": None,
                "expected_tool": test['expected_tool'],
                "actual_tool": None,
                "group_success": False,
                "tool_success": False,
                "overall_success": False,
                "error": group_result.get('error')
            })
            continue
        
        selected_group_id = group_result['selected_group_id']
        group_reasoning = group_result.get('reasoning', 'No reasoning provided')
        group_info = agent.get_group_info(selected_group_id)
        
        group_success = selected_group_id == test['expected_group']
        group_status = "✅" if group_success else "❌"
        
        print(f"{group_status} Selected Group: {selected_group_id} ({group_info['name']})")
        print(f"   Reasoning: {group_reasoning}")
        
        if not group_success:
            expected_info = agent.get_group_info(test['expected_group'])
            print(f"   ⚠️  Expected: {test['expected_group']} ({expected_info['name']})")
        
        # STEP 2: Select specific tool from the group
        print(f"\n🎯 Step 2: Selecting specific tool from '{group_info['name']}'...")
        
        # Small delay between API calls
        await asyncio.sleep(0.3)
        
        tool_result = await agent.select_specific_tool(test['query'], selected_group_id)
        
        if "error" in tool_result:
            print(f"❌ STEP 2 FAILED: {tool_result['error']}")
            if "raw_response" in tool_result:
                print(f"Raw Response: {tool_result['raw_response']}")
            results.append({
                "test_number": i,
                "query": test['query'],
                "expected_group": test['expected_group'],
                "actual_group": selected_group_id,
                "expected_tool": test['expected_tool'],
                "actual_tool": None,
                "group_success": group_success,
                "tool_success": False,
                "overall_success": False,
                "group_reasoning": group_reasoning,
                "error": tool_result.get('error')
            })
            continue
        
        selected_tool = tool_result['selected_tool']
        tool_reasoning = tool_result.get('reasoning', 'No reasoning provided')
        tool_description = group_info['tools'].get(selected_tool, 'Unknown tool')
        
        tool_success = selected_tool == test['expected_tool']
        tool_status = "✅" if tool_success else "❌"
        
        print(f"{tool_status} Selected Tool: {selected_tool}")
        print(f"   Description: {tool_description}")
        print(f"   Reasoning: {tool_reasoning}")
        
        if not tool_success:
            expected_tool_desc = group_info['tools'].get(test['expected_tool'], 'Unknown tool')
            print(f"   ⚠️  Expected: {test['expected_tool']}")
            print(f"   ⚠️  Expected Description: {expected_tool_desc}")
        
        overall_success = group_success and tool_success
        overall_status = "✅ PASSED" if overall_success else "❌ FAILED"
        
        print(f"\n{overall_status} - Overall Result")
        
        results.append({
            "test_number": i,
            "query": test['query'],
            "expected_group": test['expected_group'],
            "actual_group": selected_group_id,
            "expected_tool": test['expected_tool'],
            "actual_tool": selected_tool,
            "group_success": group_success,
            "tool_success": tool_success,
            "overall_success": overall_success,
            "group_reasoning": group_reasoning,
            "tool_reasoning": tool_reasoning
        })
        
        # Delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    total_tests = len(results)
    overall_passed = sum(1 for r in results if r['overall_success'])
    group_passed = sum(1 for r in results if r['group_success'])
    tool_passed = sum(1 for r in results if r['tool_success'])
    
    overall_success_rate = (overall_passed / total_tests * 100) if total_tests else 0
    group_success_rate = (group_passed / total_tests * 100) if total_tests else 0
    tool_success_rate = (tool_passed / total_tests * 100) if total_tests else 0
    
    print(f"Total Tests: {total_tests}")
    print()
    print("📊 Overall Results (Both Steps Must Pass):")
    print(f"   Passed: {overall_passed}/{total_tests}")
    print(f"   Failed: {total_tests - overall_passed}/{total_tests}")
    print(f"   Success Rate: {overall_success_rate:.1f}%")
    print()
    print("📊 Step 1 - Group Selection:")
    print(f"   Correct: {group_passed}/{total_tests}")
    print(f"   Incorrect: {total_tests - group_passed}/{total_tests}")
    print(f"   Success Rate: {group_success_rate:.1f}%")
    print()
    print("📊 Step 2 - Tool Selection:")
    print(f"   Correct: {tool_passed}/{total_tests}")
    print(f"   Incorrect: {total_tests - tool_passed}/{total_tests}")
    print(f"   Success Rate: {tool_success_rate:.1f}%")
    print()
    
    # Show failed tests
    failed_tests = [r for r in results if not r['overall_success']]
    if failed_tests:
        print("❌ Failed Tests:")
        for r in failed_tests:
            print(f"\n  Test {r['test_number']}: {r['query']}")
            if not r['group_success']:
                print(f"    ❌ Group: Expected '{r['expected_group']}', Got '{r['actual_group']}'")
            else:
                print(f"    ✅ Group: '{r['actual_group']}' (correct)")
            
            if not r['tool_success']:
                print(f"    ❌ Tool: Expected '{r['expected_tool']}', Got '{r['actual_tool']}'")
            else:
                print(f"    ✅ Tool: '{r['actual_tool']}' (correct)")
    else:
        print("🎉 All tests passed!")
    
    print("\n" + "=" * 80)
    print("DETAILED RESULTS (JSON)")
    print("=" * 80)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(test_hierarchical_tool_selection())

