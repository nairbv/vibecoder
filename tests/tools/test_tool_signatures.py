from vibecoder.tools import get_all_tools

def test_tool_signatures():
    tools = get_all_tools()
    for tool in tools:
        signature = tool.signature
        assert 'type' in signature, f"Tool {tool.name} is missing 'type' in signature."
        assert signature['type'] == 'function', f"Tool {tool.name} 'type' should be 'function'."
