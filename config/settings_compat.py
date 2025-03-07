"""
Compatibility layer for Settings class.

This module provides backward compatibility for code that expects a Settings class,
but now uses the Config class.
"""

from config.settings import Config

# For backward compatibility
class Settings(Config):
    """Compatibility class that inherits from Config for backward compatibility."""
    
    def get_config(self):
        """Get configuration dictionary."""
        return self.get_all()
    
    def get_api_key(self):
        """Get API key from configuration."""
        return self.get("api_key") or self.get("openai_api_key") or "" 