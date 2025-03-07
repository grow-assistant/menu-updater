"""
Utility for loading and managing prompt templates.

This module provides functionality to load, format, and manage prompt templates
from text files, supporting variable substitution and template caching.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from string import Template
import time
import logging

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    A class for loading and managing prompt templates.
    Includes caching and template formatting functionality.
    """
    
    def __init__(self, template_dir: str = "resources/prompts/templates"):
        """
        Initialize the prompt loader.
        
        Args:
            template_dir: Directory containing prompt templates
        """
        self.template_dir = template_dir
        self.templates = {}  # Cache for loaded templates
        
        # Performance metrics
        self.cache_hits = 0
        self.cache_misses = 0
        self.load_times = {}
        
        logger.info(f"PromptLoader initialized with template directory: {template_dir}")
    
    def load_template(self, template_name: str, force_reload: bool = False) -> str:
        """
        Load a template from a file.
        
        Args:
            template_name: Name of the template (without extension)
            force_reload: Whether to force reload even if the template is cached
            
        Returns:
            The template content as a string
        """
        start_time = time.time()
        
        # If template is in cache and not forcing reload, return cached version
        if template_name in self.templates and not force_reload:
            self.cache_hits += 1
            logger.debug(f"Template cache hit: {template_name}")
            return self.templates[template_name]
        
        self.cache_misses += 1
        logger.debug(f"Template cache miss: {template_name}")
        
        # Look for the template file
        file_path = Path(self.template_dir) / f"{template_name}.txt"
        if not file_path.exists() or not file_path.is_file():
            logger.warning(f"Template file not found: {file_path}")
            return ""
        
        # Load the template
        try:
            with open(file_path, "r") as f:
                template = f.read()
            
            # Store in cache
            self.templates[template_name] = template
            
            # Update load time metrics
            load_time = time.time() - start_time
            self.load_times[template_name] = load_time
            logger.debug(f"Loaded template '{template_name}' in {load_time:.4f}s")
            
            return template
        except Exception as e:
            logger.error(f"Error loading template '{template_name}': {e}")
            return ""
            
    def format_template(self, template_name: str, **kwargs) -> str:
        """
        Format a template by substituting variables.
        
        Args:
            template_name: Name of the template
            **kwargs: Variables to substitute
            
        Returns:
            Formatted template as a string
        """
        start_time = time.time()
        
        # Load the template
        template = self.load_template(template_name)
        if not template:
            return ""
        
        # Format the template
        try:
            # For each key in kwargs, replace ${key} with the value
            formatted = template
            for key, value in kwargs.items():
                placeholder = "${" + key + "}"
                formatted = formatted.replace(placeholder, str(value))
            
            format_time = time.time() - start_time
            logger.debug(f"Formatted template '{template_name}' in {format_time:.4f}s")
            
            return formatted
        except Exception as e:
            logger.error(f"Error formatting template '{template_name}': {e}")
            return template  # Return the unformatted template if formatting fails
    
    def list_templates(self) -> List[str]:
        """
        List all available template files.
        
        Returns:
            List of template names (without extensions)
        """
        template_dir = Path(self.template_dir)
        if not template_dir.exists():
            return []
        
        templates = []
        for file_path in template_dir.glob("*.*"):
            if file_path.suffix in (".txt", ".md", ".template"):
                templates.append(file_path.stem)
        
        return templates
    
    def create_template(self, template_name: str, content: str, 
                        overwrite: bool = False) -> bool:
        """
        Create a new template file.
        
        Args:
            template_name: Name for the template (without extension)
            content: Template content
            overwrite: Whether to overwrite existing template
            
        Returns:
            True if template was created successfully, False otherwise
        """
        file_path = Path(self.template_dir) / f"{template_name}.txt"
        
        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists and overwrite is not allowed
        if file_path.exists() and not overwrite:
            logger.warning(f"Template '{template_name}' already exists.")
            return False
        
        # Write the template file
        try:
            with open(file_path, "w") as f:
                f.write(content)
            
            # Update cache
            self.templates[template_name] = content
            
            logger.info(f"Template '{template_name}' created successfully.")
            return True
        except Exception as e:
            logger.error(f"Error creating template '{template_name}': {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the template cache.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.cache_hits + self.cache_misses
        hit_ratio = self.cache_hits / total_requests if total_requests > 0 else 0
        
        stats = {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_ratio": hit_ratio,
            "templates_cached": len(self.templates),
            "load_times": self.load_times
        }
        
        return stats
    
    def clear_cache(self) -> None:
        """Clear the template cache."""
        self.templates = {}
        logger.info("Template cache cleared.")


# Singleton instance for global use
_prompt_loader = None

def get_prompt_loader(template_dir: Optional[str] = None) -> PromptLoader:
    """
    Get or create the global PromptLoader instance.
    
    Args:
        template_dir: Optional directory to use for templates
        
    Returns:
        The PromptLoader instance
    """
    global _prompt_loader
    
    if _prompt_loader is None:
        _prompt_loader = PromptLoader(template_dir or "resources/prompts/templates")
    elif template_dir is not None:
        # Update template directory if provided
        _prompt_loader.template_dir = template_dir
    
    return _prompt_loader 