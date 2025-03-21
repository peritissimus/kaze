"""
Language registry for Tree-sitter parsers.
This module manages the registration and access to language-specific parsers.
"""

from typing import Dict, Type, Optional
from kaze.languages.base import BaseLanguageParser

# Registry of language parsers
_LANGUAGE_PARSERS: Dict[str, Type[BaseLanguageParser]] = {}

def register_language(language_id: str, parser_class: Type[BaseLanguageParser]):
    """Register a language parser class."""
    _LANGUAGE_PARSERS[language_id] = parser_class
    print(f"Registered language parser for: {language_id}")

def get_language_parser(language_id: str) -> Optional[Type[BaseLanguageParser]]:
    """Get a language parser class by language ID."""
    return _LANGUAGE_PARSERS.get(language_id)

def get_supported_languages() -> Dict[str, Type[BaseLanguageParser]]:
    """Get all supported languages."""
    return _LANGUAGE_PARSERS.copy()

# Import all language parsers to register them
from kaze.languages.python import PythonParser
from kaze.languages.javascript import JavaScriptParser
from kaze.languages.typescript import TypeScriptParser
from kaze.languages.java import JavaParser
# Add more imports for other languages as needed
