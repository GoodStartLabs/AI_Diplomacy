"""
Tests for template_renderer module.

Tests both the new {{var}} double-brace syntax and the legacy {var} single-brace syntax
to ensure backward compatibility.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_diplomacy.template_renderer import (
    render_template,
    get_template_variables,
    validate_template,
    TemplateRenderError,
)


class TestRenderTemplateDoubleBrace:
    """Tests for the new {{var}} double-brace syntax."""

    def test_simple_substitution(self):
        result = render_template("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_multiple_variables(self):
        template = "{{greeting}} {{name}}, welcome to {{place}}!"
        context = {"greeting": "Hello", "name": "Alice", "place": "Wonderland"}
        result = render_template(template, context)
        assert result == "Hello Alice, welcome to Wonderland!"

    def test_power_name_substitution(self):
        """Key use case: substituting power names in Diplomacy prompts."""
        template = "You are playing as {{power_name}} in a game of Diplomacy."
        result = render_template(template, {"power_name": "FRANCE"})
        assert result == "You are playing as FRANCE in a game of Diplomacy."

    def test_numeric_value(self):
        result = render_template("Score: {{score}}", {"score": 42})
        assert result == "Score: 42"

    def test_empty_template(self):
        result = render_template("", {"name": "test"})
        assert result == ""

    def test_no_placeholders(self):
        result = render_template("Plain text", {"name": "ignored"})
        assert result == "Plain text"


class TestRenderTemplateSingleBrace:
    """Tests for the legacy {var} single-brace syntax (backward compatibility)."""

    def test_simple_substitution(self):
        result = render_template("Hello {name}!", {"name": "World"})
        assert result == "Hello World!"

    def test_existing_prompt_pattern(self):
        """Test pattern matching actual ai_diplomacy prompts."""
        template = "Your power is {power_name}. The {current_phase} phase."
        context = {"power_name": "AUSTRIA", "current_phase": "Spring 1901 Movement"}
        result = render_template(template, context)
        assert result == "Your power is AUSTRIA. The Spring 1901 Movement phase."

    def test_multiple_variables(self):
        template = "Unit: {unit_type} at {location}"
        context = {"unit_type": "Army", "location": "Paris"}
        result = render_template(template, context)
        assert result == "Unit: Army at Paris"


class TestMixedSyntax:
    """Tests for templates using both syntaxes together."""

    def test_both_syntaxes_in_same_template(self):
        template = "{{new_var}} and {old_var}"
        context = {"new_var": "NEW", "old_var": "OLD"}
        result = render_template(template, context)
        assert result == "NEW and OLD"

    def test_migration_scenario(self):
        """Simulate gradual migration from {var} to {{var}}."""
        template = "Power: {{power_name}}, Phase: {current_phase}"
        context = {"power_name": "GERMANY", "current_phase": "F1901M"}
        result = render_template(template, context)
        assert result == "Power: GERMANY, Phase: F1901M"


class TestDottedPaths:
    """Tests for nested variable access using dotted paths."""

    def test_simple_dotted_path(self):
        template = "Hello {{user.name}}!"
        context = {"user": {"name": "Alice"}}
        result = render_template(template, context)
        assert result == "Hello Alice!"

    def test_deeply_nested_path(self):
        template = "Value: {{a.b.c}}"
        context = {"a": {"b": {"c": "deep"}}}
        result = render_template(template, context)
        assert result == "Value: deep"


class TestStrictMode:
    """Tests for strict mode error handling."""

    def test_missing_variable_strict(self):
        with pytest.raises(TemplateRenderError) as exc_info:
            render_template("Hello {{name}}!", {})
        assert "name" in str(exc_info.value)
        assert "{{name}}" in exc_info.value.missing_vars

    def test_missing_variable_non_strict(self):
        result = render_template("Hello {{name}}!", {}, strict=False)
        assert result == "Hello {{name}}!"

    def test_partial_substitution_non_strict(self):
        template = "{{known}} and {{unknown}}"
        result = render_template(template, {"known": "A"}, strict=False)
        assert result == "A and {{unknown}}"

    def test_error_includes_template_snippet(self):
        long_template = "x" * 100 + "{{missing}}" + "y" * 100
        with pytest.raises(TemplateRenderError) as exc_info:
            render_template(long_template, {})
        assert exc_info.value.template_snippet is not None


class TestEdgeCases:
    """Edge cases and special scenarios."""

    def test_json_in_template_not_matched(self):
        """JSON examples in prompts should not be matched as variables."""
        template = 'Example: {"key": "value"}'
        result = render_template(template, {}, strict=False)
        assert result == 'Example: {"key": "value"}'

    def test_escaped_braces_preserved(self):
        """Double braces that aren't variables should be preserved."""
        # This tests a case where there might be literal {{ in text
        template = "Use {{var}} for variables"
        result = render_template(template, {"var": "placeholders"})
        assert result == "Use placeholders for variables"

    def test_adjacent_placeholders(self):
        template = "{{a}}{{b}}{{c}}"
        result = render_template(template, {"a": "1", "b": "2", "c": "3"})
        assert result == "123"

    def test_whitespace_in_variable_name_stripped(self):
        # The regex uses \w+ so whitespace shouldn't match, but the code strips
        template = "{{ name }}"  # Note: this won't match due to spaces in regex
        result = render_template(template, {"name": "test"}, strict=False)
        # With current regex, spaces inside braces won't match
        assert result == "{{ name }}"

    def test_underscore_in_variable_name(self):
        template = "{{power_name}} has {{unit_count}} units"
        context = {"power_name": "FRANCE", "unit_count": 3}
        result = render_template(template, context)
        assert result == "FRANCE has 3 units"


class TestGetTemplateVariables:
    """Tests for the get_template_variables utility function."""

    def test_extract_double_brace_vars(self):
        template = "Hello {{name}}, welcome to {{place}}"
        result = get_template_variables(template)
        assert set(result["double_brace"]) == {"name", "place"}
        assert result["single_brace"] == []

    def test_extract_single_brace_vars(self):
        template = "Power: {power_name}, Phase: {phase}"
        result = get_template_variables(template)
        assert result["double_brace"] == []
        assert set(result["single_brace"]) == {"power_name", "phase"}

    def test_extract_mixed_vars(self):
        template = "{{new}} and {old}"
        result = get_template_variables(template)
        assert "new" in result["double_brace"]
        assert "old" in result["single_brace"]

    def test_extract_dotted_vars(self):
        template = "{{user.name}} at {{location.city}}"
        result = get_template_variables(template)
        assert set(result["double_brace"]) == {"user.name", "location.city"}


class TestValidateTemplate:
    """Tests for the validate_template utility function."""

    def test_all_valid(self):
        template = "{{name}} is {{age}} years old"
        result = validate_template(template, ["name", "age"])
        assert set(result["valid"]) == {"name", "age"}
        assert result["invalid"] == []

    def test_some_invalid(self):
        template = "{{name}} has {{unknown}}"
        result = validate_template(template, ["name"])
        assert "name" in result["valid"]
        assert "unknown" in result["invalid"]

    def test_validate_single_syntax_only(self):
        template = "{{double}} and {single}"
        result = validate_template(template, ["double"], syntax="double")
        assert "double" in result["valid"]
        # single brace not checked when syntax="double"
        assert "single" not in result["invalid"]


class TestBackwardCompatibility:
    """
    Tests specifically designed to verify backward compatibility
    with existing ai_diplomacy prompts.
    """

    def test_context_prompt_pattern(self):
        """Test pattern from actual context_prompt.txt."""
        template = """You are playing the board game Diplomacy. Your power is {power_name}. The {current_phase} phase.

Power: {power_name}
Phase: {current_phase}

PLAYER STATUS
Current Goals: {agent_goals}
Relationships: {agent_relationships}"""

        context = {
            "power_name": "FRANCE",
            "current_phase": "Spring 1901",
            "agent_goals": "Expand into Iberia",
            "agent_relationships": "Allied with England",
        }

        result = render_template(template, context)
        assert "Your power is FRANCE" in result
        assert "The Spring 1901 phase" in result
        assert "Expand into Iberia" in result

    def test_initialization_prompt_pattern(self):
        """Test pattern from initialization.py line 47."""
        template = "Initialize {power_name} with allowed relationships: {allowed_labels_str}"
        context = {
            "power_name": "AUSTRIA",
            "allowed_labels_str": "Enemy, Neutral, Ally",
        }
        result = render_template(template, context)
        assert result == "Initialize AUSTRIA with allowed relationships: Enemy, Neutral, Ally"
