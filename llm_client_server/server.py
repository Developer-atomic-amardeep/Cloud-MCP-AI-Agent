import os
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="knowledge_base",
    host="0.0.0.0",
    port=8050,
)

@mcp.tool()

def get_knowledge_base(query: str) -> str:
    """Get the knowledge base"""

    try:
        kb_path = os.path.join(os.path.dirname(__file__), "data", "company_policies.json")
        with open(kb_path, "r") as f:
            kb_data = json.load(f)
        
        kb_text = "Here is the retrieved knowledge base:\n \n"

        if isinstance(kb_data, list):
            for i, item in enumerate(kb_data, 1):
                if isinstance(item, dict):
                    question = item.get("question", "Unknown Question")
                    answer = item.get("answer", "Unknown Answer")
                else:
                    question = f"Item {i}"
                    answer = str(item)

                kb_text += f"Q{i}: {question}\n"
                kb_text += f"A{i}: {answer}\n\n"

        else:
            kb_text += f"knowledge base content {json.dumps(kb_data, indent=2)}\n\n"

        return kb_text
        
    except FileNotFoundError:
        return "Knowledge base file not found"

    except json.JSONDecodeError:
        return "Error parsing knowledge base file"
    
    except Exception as e:
        return f"Error retrieving knowledge base: {str(e)}"
    

if __name__ == "__main__":
    transport = "sse"
    mcp.run(transport=transport)
