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
        ("Main Application", "app.py", "python"),
        ("Analytics", "utils/analytics.py", "python"),
        ("API Functions", "utils/api_functions.py", "python"),
        ("Chat Functions", "utils/chat_functions.py", "python"),
        ("Configuration", "utils/config.py", "python"),
        ("Database Functions", "utils/database_functions.py", "python"),
        ("Function Calling Spec", "utils/function_calling_spec.py", "python"),
        ("Help Functions", "utils/help_functions.py", "python"),
        ("Menu Analytics", "utils/menu_analytics.py", "python"),
        ("Menu Operations", "utils/menu_operations.py", "python"),
        ("System Prompts", "utils/system_prompts.py", "python"),
        ("UI Components", "utils/ui_components.py", "python"),
        ("Query Templates", "utils/query_templates.py", "python"),
        ("Peak Orders Analysis", "Swoop Queries/Peak_Orders_Analysis.pgsql", "sql"),
        ("Menu Cleanup", "Swoop Queries/Menu Management/Delete Option Items then Options/_Menu Cleanup - Delete Option Items then Options.pgsql", "sql"),
        ("Location Hours - Insert", "Swoop Queries/Location Hours/Insert Location Hours.pgsql", "sql"),
        ("Location Hours - Query", "Swoop Queries/Location Hours/locationhours.pgsql", "sql"),
        ("Location Hours - Update", "Swoop Queries/Location Hours/Update Location Hours.pgsql", "sql"),
        ("Location Hours - View", "Swoop Queries/Location Hours/View Location Hours.pgsql", "sql"),
        ("Markers - Insert", "Swoop Queries/Markers/Insert Markers.pgsql", "sql"),
        ("Markers - View", "Swoop Queries/Markers/View Markers.pgsql", "sql"),
        ("Menu Management - Delete Option Items", "Swoop Queries/Menu Management/Delete Option Items/_Menu Cleanup - Delete Option Items.pgsql", "sql"),
        ("Menu Management - Delete Option Items then Options", "Swoop Queries/Menu Management/Delete Option Items then Options/_Menu Cleanup - Delete Option Items then Options.pgsql", "sql"),
        ("Menu Management - Show Option Items then Options", "Swoop Queries/Menu Management/Delete Option Items then Options/_Menu Cleanup - Show Option Items then Options.pgsql", "sql"),
        ("Menu Management - Insert Items", "Swoop Queries/Menu Management/Insert Items.pgsql", "sql"),
        ("Menu Management - Menu Items with Options", "Swoop Queries/Menu Management/Menu Items with Options.pgsql", "sql"),
        ("Menu Management - Menu JSON", "Swoop Queries/Menu Management/menu.json", "json"),
        ("Menu Management - Open Orders", "Swoop Queries/Menu Management/Open Orders.pgsql", "sql"),
        ("Menu Management - Option Min Max Test", "Swoop Queries/Menu Management/Option Min Max/_Menu Cleanup - Update Option Min Max - Test.pgsql", "sql"),
        ("Menu Management - Option Min Max Update", "Swoop Queries/Menu Management/Option Min Max/_Menu Cleanup - Update Option Min Max.pgsql", "sql"),
        ("Menu Management - Replicate Option and Option Items Copy", "Swoop Queries/Menu Management/Replicate Option and Option Items copy.pgsql", "sql"),
        ("Menu Management - Replicate Option and Option Items", "Swoop Queries/Menu Management/Replicate Option and Option Items.pgsql", "sql"),
        ("Menu Management - Replicate Options", "Swoop Queries/Menu Management/Replicate Options.pgsql", "sql"),
        ("Menu Management - Update Option Item Name", "Swoop Queries/Menu Management/Update Option Item Name.pgsql", "sql"),
        ("Menu Management - Update Option Item Prices", "Swoop Queries/Menu Management/Update Option Item Prices.pgsql", "sql"),
        ("Menu Management - Update Selected Option", "Swoop Queries/Menu Management/Update Selected Option", "sql"),
        ("Menu Management - Clean Items and Options", "Swoop Queries/Menu Management/_Clean Items and Options.pgsql", "sql"),
        ("Menu Management - Copy All Options From Item", "Swoop Queries/Menu Management/_Copy All Options From Item.pgsql", "sql"),
        ("Menu Management - Copy One Option From Item", "Swoop Queries/Menu Management/_Copy One Option From Item.pgsql", "sql"),
        ("Menu Management - Menu Cleanup Delete", "Swoop Queries/Menu Management/_Menu Cleanup - Delete.pgsql", "sql"),
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