import os
from datetime import datetime

def create_code_section(title, file_content, language):
    """Create a markdown code section with title and content"""
    return f"## {title}\n\n```{language}\n{file_content}\n```\n\n"

def read_file_content(file_path):
    """Read content from a file, stripping line numbers"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Remove line numbers from the content (assuming format: "1|content")
            content = [line.split('|')[1] if '|' in line else line for line in file.readlines()]
            return ''.join(content)
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

def export_codebase_to_markdown():
    # Define the core files to export
    core_files = [
        ("App", "app.py", "python"),
        ("Analytics", "utils/analytics.py", "python"),
        ("API Functions", "utils/api_functions.py", "python"), 
        ("Chat Functions", "utils/chat_functions.py", "python"),
        ("Configuration", "utils/config.py", "python"),
        ("Database Functions", "utils/database_functions.py", "python"),
        ("Export Code", "export_code.py", "python"),
        ("Function Calling Spec", "utils/function_calling_spec.py", "python"),
        ("Helper Functions", "utils/helper_functions.py", "python"),
        ("Menu Analytics", "utils/menu_analytics.py", "python"),
        ("Menu Operations", "utils/menu_operations.py", "python"),
        ("Operation Patterns", "utils/operation_patterns.py", "python"),
        ("Query Templates", "utils/query_templates.py", "python"),
        ("System Prompts", "utils/system_prompts.py", "python"),
        ("UI Components", "utils/ui_components.py", "python")
    ]

    # Create markdown content
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    markdown_content = [
        f"# Menu Updater Codebase Export\n\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    ]

    # Add project overview from README
    readme_content = read_file_content("README.md")
    markdown_content.append("# Project Overview\n\n")
    markdown_content.append(readme_content)
    markdown_content.append("\n\n# Source Code\n\n")

    # Add each core file
    for title, file_path, language in core_files:
        content = read_file_content(file_path)
        markdown_content.append(create_code_section(title, content, language))

    # Write to file
    output_dir = "exports"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file = f"{output_dir}/codebase_export_{timestamp}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(markdown_content))

    print(f"Codebase exported to: {output_file}")

if __name__ == "__main__":
    export_codebase_to_markdown()