import asyncio
import json
import os
from contextlib import AsyncExitStack
from datetime import datetime
from typing import Optional, Any, Dict, List
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
from mcp.client.sse import sse_client
from mcp import ClientSession
from hierarchical_agent import HierarchicalAgent
from server_selector import ServerSelector
from unified_hierarchical_agent import UnifiedHierarchicalAgent

# Load environment variables from .env file
load_dotenv()

class MCPCerebrasClient:

    """Client for interacting with MCP servers using Cerebras API."""

    def __init__(self, model: str = "llama-4-scout-17b-16e-instruct"):
        """Initialize the MCP Cerebras client."""

        self.session: Optional[ClientSession] = None
        self.stack = AsyncExitStack()
        self.client = Cerebras(api_key=os.getenv("CEBRAS_API_KEY"))
        self.model = model
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None
        
        # Three-level hierarchical selection components
        self.server_selector = ServerSelector(model=model)
        self.unified_agent = UnifiedHierarchicalAgent(model=model)
        
        # Keep old agent for backward compatibility
        self.hierarchical_agent = HierarchicalAgent(model=model)
        
        # Track current server connection
        self.current_server_id: Optional[str] = None
        self.current_server_url: Optional[str] = None

    async def connect_to_server(self, server_url: str = "http://localhost:8051/sse/"):
        """Connect to the MCP server via SSE."""

        sse_transport = await self.stack.enter_async_context(
            sse_client(server_url)
        )
        
        self.stdio, self.write = sse_transport
        self.session = await self.stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        tools_result = await self.session.list_tools()

        
        # Check if we have the expected IAM tools
        tool_names = [tool.name for tool in tools_result.tools]
        expected_iam_tools = ['list_users', 'get_user', 'list_groups', 'list_policies', 'get_policy']
        
        if not any(tool in tool_names for tool in expected_iam_tools):
            print("\n⚠️  WARNING: This doesn't appear to be the iam-mcp-server!")
            print("Expected tools like 'list_users', 'get_user', 'list_groups', etc. are not available.")
            print("Please make sure you're running the IAM server, not the billing server.")
            print("You can run the IAM server with: python ../run_iam_server.py")
            print()

    async def connect_to_selected_server(self, server_id: str):
        """Connect to a specific server based on server ID."""
        
        server_url = self.server_selector.get_server_url(server_id)
        server_info = self.server_selector.get_server_info(server_id)
        
        print(f"🔗 Connecting to {server_info['name']}...")
        print(f"   URL: {server_url}")
        
        # Close existing connection if any
        if self.session:
            await self.cleanup()
            # Reinitialize stack for new connection
            self.stack = AsyncExitStack()
        
        # Connect to the selected server
        sse_transport = await self.stack.enter_async_context(
            sse_client(server_url)
        )
        
        self.stdio, self.write = sse_transport
        self.session = await self.stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # Validate connection by checking available tools
        tools_result = await self.session.list_tools()
        tool_names = [tool.name for tool in tools_result.tools]
        expected_tools = self.server_selector.get_expected_tools(server_id)
        
        # Check if we have at least some expected tools
        found_tools = [tool for tool in expected_tools if tool in tool_names]
        
        if not found_tools:
            print(f"\n⚠️  WARNING: Connected to server but expected tools not found!")
            print(f"Expected tools: {expected_tools}")
            print(f"Available tools: {tool_names[:10]}...")  # Show first 10 tools
        else:
            print(f"✅ Successfully connected! Found {len(found_tools)}/{len(expected_tools)} expected tools")
        
        # Update connection state
        self.current_server_id = server_id
        self.current_server_url = server_url
        
        return len(found_tools) > 0

    def clean_schema_for_cerebras(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Clean JSON schema to remove fields unsupported by Cerebras."""
        if not isinstance(schema, dict):
            return schema
        
        # Extended list of fields that Cerebras doesn't support
        unsupported_fields = {
            'maximum', 'minimum', 'exclusiveMaximum', 'exclusiveMinimum', 
            'multipleOf', 'format', 'pattern', 'const', 'examples',
            'minLength', 'maxLength', 'minItems', 'maxItems',
            'uniqueItems', 'minProperties', 'maxProperties',
            'patternProperties', 'dependencies', 'additionalItems',
            'contains', 'contentEncoding', 'contentMediaType',
            'if', 'then', 'else', 'allOf', 'oneOf', 'not'
        }
        
        cleaned = {}
        for key, value in schema.items():
            if key in unsupported_fields:
                continue
            elif isinstance(value, dict):
                cleaned[key] = self.clean_schema_for_cerebras(value)
            elif isinstance(value, list):
                cleaned[key] = [self.clean_schema_for_cerebras(item) if isinstance(item, dict) else item for item in value]
            else:
                cleaned[key] = value
        
        # Ensure object types have proper structure for Cerebras
        if cleaned.get('type') == 'object':
            # Cerebras requires additionalProperties to be false for all objects
            cleaned['additionalProperties'] = False
            
            # Ensure properties exist if none are defined and no anyOf is present
            if 'properties' not in cleaned and 'anyOf' not in cleaned:
                cleaned['properties'] = {}
        
        return cleaned

    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get available tools from MCP server in Cerebras format."""

        tool_result = await self.session.list_tools()

        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": self.clean_schema_for_cerebras(tool.inputSchema),
                },
            }
            for tool in tool_result.tools
        ]
    
    async def get_filtered_tools_for_group(self, server_id: str, group_id: str) -> List[Dict[str, Any]]:
        """Get tools filtered by the selected server and group."""
        
        all_tools = await self.get_mcp_tools()
        
        # Get the tools that belong to the selected group in the selected server
        if server_id in self.unified_agent.tool_groups and group_id in self.unified_agent.tool_groups[server_id]:
            group_tools = list(self.unified_agent.tool_groups[server_id][group_id]['tools'].keys())
            
            # Filter tools to only include those in the selected group
            filtered_tools = [
                tool for tool in all_tools 
                if tool['function']['name'] in group_tools
            ]
            
            print(f"Filtered to {len(filtered_tools)} tools from {server_id}.{group_id}: {[t['function']['name'] for t in filtered_tools]}")
            return filtered_tools
        else:
            print(f"Warning: Unknown server '{server_id}' or group '{group_id}', returning all tools")
            return all_tools

    async def process_query(self, query: str) -> str:
        """Process a query using three-level hierarchical selection and Cerebras API."""
        
        print(f"\n🔍 Processing query: {query}")
        print("=" * 80)
        
        # Show AWS configuration info (without exposing credentials)
        print("🔐 AWS Configuration:")
        aws_region = os.getenv("AWS_REGION", "Not set")
        aws_profile = os.getenv("AWS_PROFILE", "Not set")
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        print(f"   Region: {aws_region}")
        print(f"   Profile: {aws_profile}")
        print(f"   Access Key ID: {'Set' if aws_access_key else 'Not set'}")
        print(f"   Secret Access Key: {'Set' if aws_secret_key else 'Not set'}")
        
        # Check for .env file
        env_file_path = os.path.join(os.path.dirname(__file__), '.env')
        env_file_exists = os.path.exists(env_file_path)
        print(f"   .env file: {'Found' if env_file_exists else 'Not found'} at {env_file_path}")
        
        if not (aws_access_key or aws_profile):
            print("\n⚠️  AWS credentials not configured!")
            print("Please ensure your .env file contains:")
            print("   AWS_ACCESS_KEY_ID=your_access_key")
            print("   AWS_SECRET_ACCESS_KEY=your_secret_key")
            print("   AWS_REGION=us-east-1")
            print("   # OR use AWS profile:")
            print("   AWS_PROFILE=your_profile_name")
            print()
        
        print()
        
        # LEVEL 1: Server Selection
        print("🎯 LEVEL 1: Selecting appropriate MCP server...")
        server_result = await self.server_selector.select_server(query)
        
        if "error" in server_result:
            print(f"❌ Error in server selection: {server_result['error']}")
            return f"I encountered an error while selecting the appropriate server: {server_result['error']}"
        
        selected_server_id = server_result["selected_server"]
        server_reasoning = server_result.get("reasoning", "No reasoning provided")
        server_info = self.server_selector.get_server_info(selected_server_id)
        
        print(f"✅ Selected Server: {server_info['name']} ({selected_server_id})")
        print(f"💭 Server Reasoning: {server_reasoning}")
        
        # Connect to the selected server
        print(f"\n🔗 Connecting to selected server...")
        connection_success = await self.connect_to_selected_server(selected_server_id)
        
        if not connection_success:
            return f"Failed to connect to the selected server '{server_info['name']}'. Please ensure the server is running."
        
        # LEVEL 2 & 3: Tool Group and Tool Selection
        print(f"\n🎯 LEVEL 2 & 3: Selecting tool group and specific tool...")
        selection_result = await self.unified_agent.hierarchical_tool_selection(query, selected_server_id)
        
        if "error" in selection_result:
            print(f"❌ Error in tool selection: {selection_result['error']}")
            return f"I encountered an error while selecting the appropriate tool: {selection_result['error']}"
        
        selected_group = selection_result["selected_group"]
        selected_tool = selection_result["selected_tool"]
        
        print(f"✅ Selected Group: {selected_group['group_name']} ({selected_group['group_id']})")
        print(f"🎯 Selected Tool: {selected_tool['tool_name']}")
        print(f"💭 Group Reasoning: {selected_group['reasoning']}")
        print(f"💭 Tool Reasoning: {selected_tool['reasoning']}")
        
        # Get only the specifically selected tool (not the whole group)
        print(f"\n🔧 Getting the selected tool: {selected_tool['tool_name']}...")
        all_tools = await self.get_mcp_tools()
        
        # Find the specific tool that was selected
        selected_tool_schema = None
        for tool in all_tools:
            if tool['function']['name'] == selected_tool['tool_name']:
                selected_tool_schema = tool
                break
        
        if not selected_tool_schema:
            return f"Selected tool '{selected_tool['tool_name']}' not found in available tools. Please try a different query."
        
        # Use only the single selected tool to avoid schema property limits
        tools = [selected_tool_schema]
        
        # Debug: Show what parameters this tool expects
        print(f"🔍 Tool expects these parameters:")
        schema_params = selected_tool_schema['function']['parameters']
        if 'properties' in schema_params:
            for param_name, param_info in schema_params['properties'].items():
                param_type = param_info.get('type', 'unknown')
                param_desc = param_info.get('description', 'No description')
                required = param_name in schema_params.get('required', [])
                print(f"   - {param_name} ({param_type}){' [REQUIRED]' if required else ''}: {param_desc}")
        else:
            print("   - No parameters required (call with empty arguments)")
        
        # Execute query with the single selected tool
        print(f"\n🚀 EXECUTION: Processing query with the selected tool: {selected_tool['tool_name']}...")
        
        # Get current date for context
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create dynamic system message based on selected server
        if selected_server_id == "iam":
            assistant_type = "AWS IAM assistant with access to AWS IAM management tools"
            instructions = """INSTRUCTIONS:
1. You MUST call the {tool_name} function to retrieve real AWS IAM data
2. Use function calling (NOT text responses with JSON) to execute the tool
3. NEVER include 'ctx' parameter - this is handled automatically by the MCP framework
4. Only use optional parameters like 'path_prefix' or 'max_items' if specifically needed
5. For most queries, call the function with empty arguments: {{}}
6. After receiving the tool results, analyze the actual data and provide insights
7. Be helpful in explaining IAM concepts and security best practices"""
        else:  # billing
            assistant_type = "AWS cost analysis assistant with access to AWS cost management tools"
            instructions = """INSTRUCTIONS:
1. You MUST call the {tool_name} function to retrieve real AWS cost data
2. Use function calling (NOT text responses with JSON) to execute the tool
3. Calculate the correct date range based on the CURRENT DATE above
4. For cost queries, use appropriate parameters like start_date, end_date, granularity, etc.
5. Only use parameters defined in the tool schema - do NOT invent parameters
6. After receiving the tool results, analyze the actual data and provide insights"""
        
        system_content = f"""You are a helpful {assistant_type} via function calling.

CURRENT DATE: {current_date}

SERVER: {server_info['name']}
TOOL SELECTION: Based on the user's query, the most appropriate tool is:
- Tool: {selected_tool['tool_name']}
- Description: {selected_tool['tool_description']}
- Group: {selected_group['group_name']}

{instructions.format(tool_name=selected_tool['tool_name'])}

DO NOT return JSON as text - you must use function calling to invoke the tools."""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query},
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",  # Encourage tool usage
                parallel_tool_calls=False,
            )
        except Exception as e:
            print(f"❌ Error calling Cerebras API: {e}")
            
            # Debug: Check for schema issues
            if "schema" in str(e).lower() or "json" in str(e).lower() or "properties" in str(e).lower():
                print("🔍 Debugging tool schemas...")
                
                def count_properties(obj):
                    """Recursively count all properties in a schema object."""
                    count = 0
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            count += 1  # Count this property
                            if isinstance(value, (dict, list)):
                                count += count_properties(value)
                    elif isinstance(obj, list):
                        for item in obj:
                            if isinstance(item, (dict, list)):
                                count += count_properties(item)
                    return count
                
                total_properties = 0
                for i, tool in enumerate(tools):
                    print(f"Tool {i+1}: {tool['function']['name']}")
                    schema = tool['function']['parameters']
                    tool_properties = count_properties(schema)
                    total_properties += tool_properties
                    print(f"  Properties in this tool: {tool_properties}")
                    print(f"  Schema keys: {list(schema.keys())}")
                    
                    # Check for any remaining unsupported fields
                    def find_unsupported_fields(obj, path=""):
                        unsupported = []
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if key in {'minLength', 'maxLength', 'minItems', 'maxItems', 'pattern', 'format'}:
                                    unsupported.append(f"{path}.{key}" if path else key)
                                elif isinstance(value, (dict, list)):
                                    unsupported.extend(find_unsupported_fields(value, f"{path}.{key}" if path else key))
                        elif isinstance(obj, list):
                            for i, item in enumerate(obj):
                                if isinstance(item, (dict, list)):
                                    unsupported.extend(find_unsupported_fields(item, f"{path}[{i}]"))
                        return unsupported
                    
                    unsupported = find_unsupported_fields(schema)
                    if unsupported:
                        print(f"  ⚠️  Found unsupported fields: {unsupported}")
                    else:
                        print(f"  ✅ Schema appears clean")
                
                print(f"\n📊 Total properties across all tools: {total_properties}")
                print(f"   Cerebras limit: 100 properties")
                print(f"   Status: {'✅ Within limit' if total_properties <= 100 else '❌ Exceeds limit'}")
            
            raise

        choice = response.choices[0].message
        
        # Debug: Check what we got back
        print(f"\n🔍 Debug - Response type:")
        print(f"   Has tool_calls: {choice.tool_calls is not None and len(choice.tool_calls) > 0 if choice.tool_calls else False}")
        print(f"   Has content: {choice.content is not None}")
        if choice.content:
            print(f"   Content preview: {choice.content[:200]}")

        if choice.tool_calls:
            print(f"\nStep 4: Executing tool calls...")
            
            # Add the assistant's tool call message to maintain conversation flow
            messages.append({
                "role": "assistant",
                "content": choice.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function", 
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    } for tool_call in choice.tool_calls
                ]
            })
            
            for tool_call in choice.tool_calls:
                # Parse arguments and remove null values
                arguments = json.loads(tool_call.function.arguments)
                
                # Special handling for MCP context parameter
                if 'ctx' in arguments and isinstance(arguments['ctx'], dict):
                    # Replace hallucinated ctx with proper minimal MCP context
                    print(f"   🔧 Replacing hallucinated 'ctx' with proper MCP context")
                    arguments['ctx'] = {
                        "_meta": None,
                        "content": [],
                        "structuredContent": {},
                        "isError": False
                    }
                elif 'ctx' not in arguments:
                    # Add minimal MCP context if missing
                    print(f"   🔧 Adding required MCP context parameter")
                    arguments['ctx'] = {
                        "_meta": None,
                        "content": [],
                        "structuredContent": {},
                        "isError": False
                    }
                
                # Filter out None/null values (including string "null") to avoid validation errors
                filtered_arguments = {
                    k: v for k, v in arguments.items() 
                    if v is not None and v != "null" and v != ""
                }
                
                print(f"🔧 Executing function '{tool_call.function.name}' with arguments {json.dumps(filtered_arguments)}")

                result = await self.session.call_tool(
                    tool_call.function.name, 
                    arguments=filtered_arguments
                )

                # Display the actual results from AWS
                print(f"\n📊 AWS API Results from {tool_call.function.name}:")
                print("=" * 60)
                if result.content and len(result.content) > 0:
                    try:
                        # Try to parse and pretty-print the JSON result
                        result_data = json.loads(result.content[0].text)
                        print(json.dumps(result_data, indent=2))
                        
                        # Check if there's an error in the result
                        if isinstance(result_data, dict) and result_data.get("status") == "error":
                            print(f"\n❌ AWS API Error: {result_data.get('message', 'Unknown error')}")
                            print(f"Error Type: {result_data.get('error_type', 'Unknown')}")
                            if result_data.get('details'):
                                print(f"Details: {result_data.get('details')}")
                    except json.JSONDecodeError:
                        # If it's not JSON, just print the raw text
                        print(result.content[0].text)
                else:
                    print("No data returned from AWS API")
                print("=" * 60)

                messages.append({
                    "role": "tool",
                    "content": result.content[0].text,  # Don't double-encode JSON
                    "tool_call_id": tool_call.id
                })

            print(f"\nStep 5: Generating final response...")
            
            # Debug: Show what messages we're sending to the final LLM call
            print(f"🔍 Debug - Messages being sent to final LLM call:")
            for i, msg in enumerate(messages):
                print(f"   Message {i+1}: {msg['role']}")
                if msg['role'] == 'tool':
                    print(f"      Tool call ID: {msg.get('tool_call_id', 'N/A')}")
                    print(f"      Content preview: {msg['content'][:200]}...")
                elif msg['role'] == 'assistant' and 'tool_calls' in msg:
                    print(f"      Tool calls: {len(msg.get('tool_calls', []))} calls")
                    if msg.get('content'):
                        print(f"      Content preview: {msg['content'][:200]}...")
                    else:
                        print(f"      Content: None (tool calls only)")
                else:
                    content = msg.get('content', '')
                    if content:
                        print(f"      Content preview: {content[:200]}...")
                    else:
                        print(f"      Content: None")
            
            try:
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
            except Exception as e:
                print(f"❌ Error in final API call: {e}")
                raise

            return final_response.choices[0].message.content
    
        # Fallback: If no tool calls, check if content looks like a JSON tool call
        if choice.content:
            content = choice.content.strip()
            # Check if the response looks like a JSON tool call
            if content.startswith('{') and '"name"' in content and '"arguments"' in content:
                print("\n⚠️  LLM returned JSON as text instead of using function calling.")
                print("   This is a known issue with some models. Attempting to parse and execute...")
                try:
                    tool_call_data = json.loads(content)
                    tool_name = tool_call_data.get('name')
                    arguments_str = tool_call_data.get('arguments', {})
                    
                    # Parse arguments if they're a string
                    if isinstance(arguments_str, str):
                        arguments = json.loads(arguments_str) if arguments_str.startswith('{') else json.loads(arguments_str.replace("'", '"'))
                    else:
                        arguments = arguments_str
                    
                    # Filter out null values
                    filtered_arguments = {
                        k: v for k, v in arguments.items() 
                        if v is not None and v != "null" and v != ""
                    }
                    
                    print(f"\n🔧 Manually executing function '{tool_name}' with arguments:")
                    print(f"   {json.dumps(filtered_arguments, indent=2)}")
                    
                    result = await self.session.call_tool(tool_name, arguments=filtered_arguments)
                    
                    # Display the results
                    print(f"\n📊 AWS API Results from {tool_name}:")
                    print("=" * 60)
                    if result.content and len(result.content) > 0:
                        try:
                            result_data = json.loads(result.content[0].text)
                            print(json.dumps(result_data, indent=2))
                            
                            if isinstance(result_data, dict) and result_data.get("status") == "error":
                                print(f"\n❌ AWS API Error: {result_data.get('message', 'Unknown error')}")
                                return f"Error retrieving AWS cost data: {result_data.get('message', 'Unknown error')}"
                            
                            # Send the results to the LLM for analysis
                            print(f"\nStep 4: Generating analysis of the AWS data...")
                            
                            # Add the tool result to messages
                            messages.append({
                                "role": "assistant",
                                "content": content  # The original JSON response
                            })
                            messages.append({
                                "role": "user",
                                "content": f"Here are the results from AWS:\n\n{json.dumps(result_data, indent=2)}\n\nPlease analyze this AWS cost data and provide:\n1. A clear summary of the costs\n2. Daily breakdown\n3. Total cost for the period\n4. Any trends or insights\n5. Recommendations if applicable"
                            })
                            
                            try:
                                final_response = self.client.chat.completions.create(
                                    model=self.model,
                                    messages=messages,
                                )
                                return final_response.choices[0].message.content
                            except Exception as e:
                                print(f"Error generating analysis: {e}")
                                return f"Successfully retrieved AWS cost data, but couldn't generate analysis. Raw data:\n\n{json.dumps(result_data, indent=2)}"
                            
                        except json.JSONDecodeError:
                            print(result.content[0].text)
                            return result.content[0].text
                    else:
                        print("No data returned from AWS API")
                        return "No data was returned from the AWS API."
                    
                except Exception as e:
                    print(f"\n❌ Error parsing/executing manual tool call: {e}")
                    return f"I tried to retrieve your AWS cost data but encountered an error: {str(e)}\n\nOriginal response: {content}"
        
        return choice.content

    async def cleanup(self):
        """Cleanup the resources."""
        await self.stack.aclose()

async def main():
    client = MCPCerebrasClient()
    try:
        # Test with a query that could go to either server
        query = "Show me all the IAM users in my AWS account and their access keys status. I want to see the actual data from my account."
        
        print("🚀 THREE-LEVEL HIERARCHICAL MCP CLIENT TEST")
        print("=" * 80)
        print("Testing: Server Selection → Tool Group Selection → Tool Selection")
        print("=" * 80)
        
        response = await client.process_query(query)
        
        print("\n" + "=" * 80)
        print("FINAL RESPONSE:")
        print("=" * 80)
        print(response)
        
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
