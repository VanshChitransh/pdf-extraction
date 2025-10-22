"""
Prompt Engineering Module for AI Cost Estimation

This module provides the infrastructure for transforming enriched inspection data
into AI-ready prompts that produce accurate, reliable cost estimates.

Components:
- prompt_templates: System context and few-shot examples
- prompt_builder: Dynamic prompt assembly
- context_manager: Token budget and batching
- output_validator: Response validation
- version_control: Prompt testing and iteration
- specialist_prompts: Trade-specific expertise (Phase 1)
"""

from .prompt_builder import EstimationPromptBuilder
from .context_manager import ContextManager
from .output_validator import OutputValidator
from .version_control import PromptVersionControl
from .specialist_prompts import SpecialistPromptSelector

__all__ = [
    'EstimationPromptBuilder',
    'ContextManager',
    'OutputValidator',
    'PromptVersionControl',
    'SpecialistPromptSelector'
]

