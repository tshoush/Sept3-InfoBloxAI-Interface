#!/usr/bin/env python3
"""Generate HTML for MCP tools dynamically."""

def generate_tools_html(tools):
    """Generate HTML for tools list."""
    html = []
    
    for tool in tools:
        # Determine method badge color
        method_class = {
            'GET': 'method-get',
            'POST': 'method-post',
            'PUT': 'method-put',
            'DELETE': 'method-delete'
        }.get(tool.get('method', 'GET'), 'method-get')
        
        # Generate parameter HTML
        params_html = []
        for param in tool.get('parameters', []):
            required = '*' if param.get('required') else ' (optional)'
            param_html = f'''
                <div class="parameter-group">
                    <label class="parameter-label">
                        {param['name']}<span class="{'parameter-required' if param.get('required') else 'text-muted'}">{required}</span>
                    </label>
                    <input type="text" class="parameter-input" id="param-{tool['name']}-{param['name']}" 
                        placeholder="{param.get('description', '')}">
                    <div class="parameter-hint">{param.get('description', '')}</div>
                </div>'''
            params_html.append(param_html)
        
        # Generate tool card HTML
        tool_html = f'''
            <div class="tool-card" data-category="{tool.get('category', 'other')}" data-method="{tool.get('method', 'GET')}" data-tool="{tool['name']}">
                <div class="tool-header">
                    <div class="tool-name">
                        <span class="tool-category category-{tool.get('category', 'other')}">{tool.get('category', 'other').upper()}</span>
                        {tool.get('displayName', tool['name'])}
                    </div>
                    <span class="tool-method {method_class}">{tool.get('method', 'GET')}</span>
                </div>
                <div class="tool-description">
                    {tool.get('description', '')}
                </div>
                <div class="tool-path">{tool.get('path', '/wapi/v2.13.1/')}</div>
                <div class="tool-actions">
                    <button class="tool-expand" onclick="toggleTool('{tool['name']}')">
                        <i class="fas fa-play"></i> Test Tool
                    </button>
                </div>
                <div class="tool-testing" id="test-{tool['name']}" style="display: none;">
                    <h6>Parameters</h6>
                    {''.join(params_html)}
                    <button class="execute-button" onclick="executeTool('{tool['name']}', '{tool.get('method', 'GET')}')">
                        <i class="fas fa-rocket"></i> Execute {tool.get('method', 'GET')}
                    </button>
                    <div class="result-container" id="result-{tool['name']}"></div>
                </div>
            </div>'''
        
        html.append(tool_html)
    
    return '\n'.join(html)

if __name__ == '__main__':
    # Test with sample tools
    import json
    from pathlib import Path
    
    tools_file = Path.home() / '.infoblox_mcp' / 'tools' / 'discovered_tools.json'
    if tools_file.exists():
        with open(tools_file) as f:
            data = json.load(f)
            tools = data.get('tools', [])
            
        html = generate_tools_html(tools[:3])  # Test with first 3 tools
        print("Generated HTML for first 3 tools:")
        print("=" * 50)
        print(html[:500] + "...")  # Show first 500 chars
        print("=" * 50)
        print(f"Total HTML length: {len(html)} characters")