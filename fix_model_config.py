"""
This script fixes the model naming issue with gpt-4o-mini.
It will update the configuration to use the correct model name format.
"""
from ai_agent.utils.config_loader import load_config
import json
import os

def main():
    print("Checking and fixing OpenAI model configuration...")
    
    # Load the current config
    config = load_config()
    
    # Check if response service config exists
    if "services" not in config:
        config["services"] = {}
    
    if "response" not in config["services"]:
        config["services"]["response"] = {}
    
    # Check current model configuration
    current_model = config["services"]["response"].get("model", "gpt-4o")
    print(f"Current model configuration: {current_model}")
    
    # Fix the model name format (lowercase with hyphen is OpenAI's standard format)
    if current_model == "gpt-4o-mini":
        config["services"]["response"]["model"] = "gpt-4o-mini"
        print("Updated model name from 'gpt-4o-mini' to 'gpt-4o-mini'")
    
    # Other possible model name fixes
    model_mappings = {
        "gpt-4o": "gpt-4o",
        "GPT-4": "gpt-4",
        "GPT-3.5-turbo": "gpt-3.5-turbo"
    }
    
    if current_model in model_mappings:
        config["services"]["response"]["model"] = model_mappings[current_model]
        print(f"Updated model name from '{current_model}' to '{model_mappings[current_model]}'")
    
    # Show the updated configuration
    print("\nUpdated configuration:")
    print(json.dumps(config["services"]["response"], indent=2))
    
    # Option to save the config
    save = input("\nSave this configuration to config.json? (y/n): ")
    if save.lower() == 'y':
        config_path = os.path.join(os.getcwd(), "config.json")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Configuration saved to {config_path}")
    else:
        print("Configuration not saved. You can manually update your config.")
    
    print("\nTo use this configuration in test_query.py, update the config loading code:")
    print("config = load_config()")
    print("config['services']['response']['model'] = 'gpt-4o-mini'  # Ensure lowercase format")

if __name__ == "__main__":
    main() 