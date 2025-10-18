#!/usr/bin/env python3
"""
Test script for the three-level hierarchical selection system.

This script tests:
1. Server Selection (IAM vs Billing)
2. Tool Group Selection (within selected server)
3. Tool Selection (within selected group)

Without actually connecting to MCP servers.
"""

import asyncio
import json
import os
from server_selector import ServerSelector
from unified_hierarchical_agent import UnifiedHierarchicalAgent


async def test_server_selection():
    """Test Level 1: Server Selection"""
    
    print("=" * 80)
    print("LEVEL 1 TEST: SERVER SELECTION")
    print("=" * 80)
    
    # Check for API key
    api_key = os.getenv("CEBRAS_API_KEY")
    if not api_key:
        print("❌ ERROR: CEBRAS_API_KEY not found in environment variables!")
        return False
    
    print(f"✅ Cerebras API Key found: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    selector = ServerSelector()
    
    # Test queries for server selection
    test_queries = [
        {
            "query": "Show me all IAM users in my AWS account",
            "expected_server": "iam",
            "description": "IAM user listing query"
        },
        {
            "query": "Create a new IAM role for Lambda execution",
            "expected_server": "iam", 
            "description": "IAM role creation query"
        },
        {
            "query": "What are my AWS costs for last month?",
            "expected_server": "billing",
            "description": "Cost analysis query"
        },
        {
            "query": "Show me cost optimization recommendations",
            "expected_server": "billing",
            "description": "Cost optimization query"
        },
        {
            "query": "List all my IAM policies and their permissions",
            "expected_server": "iam",
            "description": "IAM policy query"
        },
        {
            "query": "How much am I spending on EC2 instances?",
            "expected_server": "billing",
            "description": "EC2 cost query"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n🧪 Test {i}/{len(test_queries)}: {test['description']}")
        print(f"Query: \"{test['query']}\"")
        print(f"Expected Server: {test['expected_server']}")
        
        result = await selector.select_server(test['query'])
        
        if "error" in result:
            print(f"❌ FAILED: {result['error']}")
            results.append({"test": i, "success": False, "error": result['error']})
            continue
        
        selected_server = result['selected_server']
        reasoning = result.get('reasoning', 'No reasoning provided')
        
        success = selected_server == test['expected_server']
        status = "✅ PASSED" if success else "❌ FAILED"
        
        print(f"{status}")
        print(f"   Selected: {selected_server}")
        print(f"   Reasoning: {reasoning}")
        
        if not success:
            print(f"   ⚠️  Expected: {test['expected_server']}")
        
        results.append({
            "test": i,
            "query": test['query'],
            "expected": test['expected_server'],
            "actual": selected_server,
            "success": success,
            "reasoning": reasoning
        })
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.3)
    
    # Summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    success_rate = (passed_tests / total_tests * 100) if total_tests else 0
    
    print(f"\n📊 LEVEL 1 SUMMARY:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    print(f"   Success Rate: {success_rate:.1f}%")
    
    return success_rate >= 80  # 80% success rate threshold


async def test_tool_group_selection():
    """Test Level 2: Tool Group Selection"""
    
    print("\n" + "=" * 80)
    print("LEVEL 2 TEST: TOOL GROUP SELECTION")
    print("=" * 80)
    
    agent = UnifiedHierarchicalAgent()
    
    # Test queries for tool group selection
    test_cases = [
        {
            "server": "iam",
            "query": "List all IAM users",
            "expected_group": "user_management",
            "description": "IAM user listing"
        },
        {
            "server": "iam", 
            "query": "Create a new IAM role",
            "expected_group": "role_management",
            "description": "IAM role creation"
        },
        {
            "server": "iam",
            "query": "Attach a policy to a user",
            "expected_group": "policy_management", 
            "description": "IAM policy attachment"
        },
        {
            "server": "billing",
            "query": "Show me my AWS costs for last month",
            "expected_group": "core_cost_analysis",
            "description": "Cost analysis query"
        },
        {
            "server": "billing",
            "query": "Give me cost optimization recommendations",
            "expected_group": "optimization_recommendations",
            "description": "Cost optimization query"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}/{len(test_cases)}: {test['description']}")
        print(f"Server: {test['server']}")
        print(f"Query: \"{test['query']}\"")
        print(f"Expected Group: {test['expected_group']}")
        
        result = await agent.select_tool_group(test['query'], test['server'])
        
        if "error" in result:
            print(f"❌ FAILED: {result['error']}")
            results.append({"test": i, "success": False, "error": result['error']})
            continue
        
        selected_group = result['selected_group_id']
        reasoning = result.get('reasoning', 'No reasoning provided')
        
        success = selected_group == test['expected_group']
        status = "✅ PASSED" if success else "❌ FAILED"
        
        print(f"{status}")
        print(f"   Selected: {selected_group}")
        print(f"   Reasoning: {reasoning}")
        
        if not success:
            print(f"   ⚠️  Expected: {test['expected_group']}")
        
        results.append({
            "test": i,
            "server": test['server'],
            "query": test['query'],
            "expected": test['expected_group'],
            "actual": selected_group,
            "success": success,
            "reasoning": reasoning
        })
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.3)
    
    # Summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    success_rate = (passed_tests / total_tests * 100) if total_tests else 0
    
    print(f"\n📊 LEVEL 2 SUMMARY:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    print(f"   Success Rate: {success_rate:.1f}%")
    
    return success_rate >= 80  # 80% success rate threshold


async def test_tool_selection():
    """Test Level 3: Specific Tool Selection"""
    
    print("\n" + "=" * 80)
    print("LEVEL 3 TEST: SPECIFIC TOOL SELECTION")
    print("=" * 80)
    
    agent = UnifiedHierarchicalAgent()
    
    # Test queries for specific tool selection
    test_cases = [
        {
            "server": "iam",
            "group": "user_management",
            "query": "List all IAM users",
            "expected_tool": "list_users",
            "description": "IAM user listing"
        },
        {
            "server": "iam",
            "group": "user_management", 
            "query": "Get details about user 'admin'",
            "expected_tool": "get_user",
            "description": "IAM user details"
        },
        {
            "server": "iam",
            "group": "role_management",
            "query": "Create a new role for Lambda",
            "expected_tool": "create_role",
            "description": "IAM role creation"
        },
        {
            "server": "billing",
            "group": "core_cost_analysis",
            "query": "Show me my costs for last month",
            "expected_tool": "cost-explorer",
            "description": "Cost exploration"
        },
        {
            "server": "billing",
            "group": "optimization_recommendations",
            "query": "Give me cost optimization recommendations",
            "expected_tool": "cost-optimization",
            "description": "Cost optimization"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}/{len(test_cases)}: {test['description']}")
        print(f"Server: {test['server']}")
        print(f"Group: {test['group']}")
        print(f"Query: \"{test['query']}\"")
        print(f"Expected Tool: {test['expected_tool']}")
        
        result = await agent.select_specific_tool(test['query'], test['server'], test['group'])
        
        if "error" in result:
            print(f"❌ FAILED: {result['error']}")
            results.append({"test": i, "success": False, "error": result['error']})
            continue
        
        selected_tool = result['selected_tool']
        reasoning = result.get('reasoning', 'No reasoning provided')
        
        success = selected_tool == test['expected_tool']
        status = "✅ PASSED" if success else "❌ FAILED"
        
        print(f"{status}")
        print(f"   Selected: {selected_tool}")
        print(f"   Reasoning: {reasoning}")
        
        if not success:
            print(f"   ⚠️  Expected: {test['expected_tool']}")
        
        results.append({
            "test": i,
            "server": test['server'],
            "group": test['group'],
            "query": test['query'],
            "expected": test['expected_tool'],
            "actual": selected_tool,
            "success": success,
            "reasoning": reasoning
        })
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.3)
    
    # Summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    success_rate = (passed_tests / total_tests * 100) if total_tests else 0
    
    print(f"\n📊 LEVEL 3 SUMMARY:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    print(f"   Success Rate: {success_rate:.1f}%")
    
    return success_rate >= 80  # 80% success rate threshold


async def main():
    """Run all three levels of testing"""
    
    print("🚀 THREE-LEVEL HIERARCHICAL SELECTION TEST SUITE")
    print("=" * 80)
    print("Testing the complete three-level selection system:")
    print("1. Server Selection (IAM vs Billing)")
    print("2. Tool Group Selection (within server)")
    print("3. Specific Tool Selection (within group)")
    print("=" * 80)
    
    # Run all tests
    level1_success = await test_server_selection()
    level2_success = await test_tool_group_selection()
    level3_success = await test_tool_selection()
    
    # Overall summary
    print("\n" + "=" * 80)
    print("🎯 OVERALL TEST RESULTS")
    print("=" * 80)
    
    print(f"Level 1 (Server Selection): {'✅ PASSED' if level1_success else '❌ FAILED'}")
    print(f"Level 2 (Tool Group Selection): {'✅ PASSED' if level2_success else '❌ FAILED'}")
    print(f"Level 3 (Tool Selection): {'✅ PASSED' if level3_success else '❌ FAILED'}")
    
    overall_success = level1_success and level2_success and level3_success
    
    print(f"\n🏆 OVERALL RESULT: {'✅ ALL LEVELS PASSED' if overall_success else '❌ SOME LEVELS FAILED'}")
    
    if overall_success:
        print("\n🎉 The three-level hierarchical selection system is working correctly!")
        print("You can now use the client with confidence that it will:")
        print("   1. Select the right server (IAM or Billing)")
        print("   2. Select the right tool group within that server")
        print("   3. Select the right specific tool for the user's query")
    else:
        print("\n⚠️  Some tests failed. Please review the results above.")
        print("The system may still work but might not always select the optimal tools.")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
