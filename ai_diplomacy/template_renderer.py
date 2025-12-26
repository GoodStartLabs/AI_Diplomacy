"""
Template rendering utilities for prompt substitution.

Supports both single-brace {var} and double-brace {{var}} syntax
for backward compatibility with existing prompts while enabling
new tournament-style templates.

Usage:
    from .template_renderer import render_template

    # New style (tournament)
    result = render_template("Hello {{name}}!", {"name": "World"})

    # Legacy style (existing ai_diplomacy prompts)
    result = render_template("Power: {power_name}", {"power_name": "FRANCE"})

    # Mixed (both work together)
    result = render_template("{{new}} and {old}", {"new": "A", "old": "B"})
"""

import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class TemplateRenderError(Exception):
    """Raised when template rendering fails due to missing variables."""

    def __init__(self, missing_vars: List[str], template_snippet: str = ""):
        self.missing_vars = missing_vars
        self.template_snippet = template_snippet
        super().__init__(
            f"Missing template variables: {', '.join(missing_vars)}"
            + (f"\nTemplate snippet: {template_snippet[:200]}..." if template_snippet else "")
        )


def render_template(template: str, context: Dict[str, Any], strict: bool = True) -> str:
    """
    Render a template string by substituting placeholders with values from context.

    Supports both syntaxes for backward compatibility:
    - {{var}} - double-brace syntax (preferred, tournament style)
    - {var} - single-brace syntax (legacy, ai_diplomacy style)

    Double-brace placeholders are processed first, then single-brace.
    This allows gradual migration from {var} to {{var}} syntax.

    Args:
        template: The template string containing placeholders
        context: Dictionary mapping variable names to their values
        strict: If True (default), raise TemplateRenderError on missing variables.
                If False, leave unmatched placeholders unchanged.

    Returns:
        The rendered string with placeholders substituted

    Raises:
        TemplateRenderError: If strict=True and any placeholder variables
                             are not found in context

    Examples:
        >>> render_template("Hello {{name}}!", {"name": "World"})
        'Hello World!'

        >>> render_template("Power: {power_name}", {"power_name": "FRANCE"})
        'Power: FRANCE'

        >>> render_template("{{new}} and {old}", {"new": "A", "old": "B"})
        'A and B'
    """
    if not template:
        return template

    result = template
    missing_vars: List[str] = []

    # Pass 1: Substitute {{var}} patterns (double-brace, tournament style)
    # Supports dotted paths like {{power.name}} for future extensibility
    def replace_double_brace(match: re.Match) -> str:
        var_name = match.group(1).strip()
        value = _resolve_var(var_name, context)
        if value is not None:
            return str(value)
        else:
            if strict:
                missing_vars.append(f"{{{{{var_name}}}}}")  # {{var}} format for error msg
            return match.group(0)  # Keep original placeholder

    result = re.sub(r"\{\{([\w.]+)\}\}", replace_double_brace, result)

    # Pass 2: Substitute {var} patterns (single-brace, legacy style)
    # Uses negative lookbehind/lookahead to avoid matching {{ or }}
    def replace_single_brace(match: re.Match) -> str:
        var_name = match.group(1).strip()
        value = _resolve_var(var_name, context)
        if value is not None:
            return str(value)
        else:
            if strict:
                missing_vars.append(f"{{{var_name}}}")  # {var} format for error msg
            return match.group(0)  # Keep original placeholder

    # Match {var} but NOT {{var}} (already processed)
    # (?<!\{) - not preceded by {
    # (?!\}) - not followed by }
    result = re.sub(r"(?<!\{)\{(\w+)\}(?!\})", replace_single_brace, result)

    if strict and missing_vars:
        raise TemplateRenderError(missing_vars, template[:500])

    return result


def _resolve_var(var_path: str, context: Dict[str, Any]) -> Optional[Any]:
    """
    Resolve a variable path (potentially dotted) from context.

    Args:
        var_path: Variable name, optionally with dots for nested access (e.g., "power.name")
        context: The context dictionary

    Returns:
        The resolved value, or None if not found
    """
    # Simple case: direct key lookup
    if "." not in var_path:
        return context.get(var_path)

    # Dotted path: traverse nested structure
    parts = var_path.split(".")
    current = context
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def get_template_variables(template: str) -> Dict[str, List[str]]:
    """
    Extract all placeholder variables from a template.

    Useful for validation and documentation.

    Args:
        template: The template string to analyze

    Returns:
        Dictionary with 'double_brace' and 'single_brace' keys,
        each containing a list of variable names found

    Example:
        >>> get_template_variables("Hello {{name}}, you are {role}")
        {'double_brace': ['name'], 'single_brace': ['role']}
    """
    double_brace = re.findall(r"\{\{([\w.]+)\}\}", template)
    single_brace = re.findall(r"(?<!\{)\{(\w+)\}(?!\})", template)

    return {
        "double_brace": list(set(double_brace)),
        "single_brace": list(set(single_brace)),
    }


def validate_template(template: str, available_vars: List[str], syntax: str = "both") -> Dict[str, List[str]]:
    """
    Validate that all placeholders in a template have corresponding available variables.

    Args:
        template: The template string to validate
        available_vars: List of variable names that will be available at render time
        syntax: Which syntax to validate - "double", "single", or "both"

    Returns:
        Dictionary with 'valid' and 'invalid' keys, each containing lists of variable names

    Example:
        >>> validate_template("{{name}} is {role}", ["name", "age"])
        {'valid': ['name'], 'invalid': ['role']}
    """
    found = get_template_variables(template)
    available_set = set(available_vars)

    all_vars = []
    if syntax in ("double", "both"):
        all_vars.extend(found["double_brace"])
    if syntax in ("single", "both"):
        all_vars.extend(found["single_brace"])

    valid = [v for v in all_vars if v in available_set]
    invalid = [v for v in all_vars if v not in available_set]

    return {
        "valid": valid,
        "invalid": invalid,
    }
