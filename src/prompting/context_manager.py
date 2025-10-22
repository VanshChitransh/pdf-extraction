"""
Context Manager

Handles token budgets, batching, and context window optimization for AI API calls.
Ensures prompts stay within API limits while maximizing information density.
"""

from typing import Dict, List, Any, Tuple, Optional
import json


class ContextManager:
    """
    Manages context windows and token budgets for AI API calls.
    
    Features:
    - Token estimation for prompts
    - Issue prioritization by severity/complexity
    - Intelligent batching for cost optimization
    - Context window optimization
    
    Usage:
        manager = ContextManager(max_tokens=100000, target_tokens=80000)
        
        # Prioritize issues for processing
        prioritized = manager.prioritize_issues(all_issues)
        
        # Create optimal batches
        batches = manager.create_batches(prioritized, batch_size=10)
        
        # Check if prompt fits in budget
        if manager.fits_in_budget(prompt_messages):
            # Process prompt
    """
    
    def __init__(
        self,
        max_tokens: int = 100000,
        target_tokens: int = 80000,
        tokens_per_char: float = 0.25,
        reserve_for_response: int = 4000
    ):
        """
        Initialize context manager.
        
        Args:
            max_tokens: Maximum tokens for API (Gemini 2.5 Flash = 1M, but practical limit lower)
            target_tokens: Target to stay under (leaves headroom)
            tokens_per_char: Rough token-to-character ratio for estimation
            reserve_for_response: Tokens to reserve for AI response
        """
        self.max_tokens = max_tokens
        self.target_tokens = target_tokens
        self.tokens_per_char = tokens_per_char
        self.reserve_for_response = reserve_for_response
        
        self.stats = {
            "total_issues_processed": 0,
            "total_tokens_estimated": 0,
            "batches_created": 0,
            "issues_truncated": 0
        }
    
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text.
        
        This is a rough approximation. Actual tokens depend on the tokenizer,
        but this is sufficient for budgeting purposes.
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters (English text)
        return int(len(text) * self.tokens_per_char)
    
    def estimate_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate total tokens for a list of messages.
        
        Args:
            messages: List of message dicts [{"role": "system", "content": "..."}, ...]
        
        Returns:
            Estimated total tokens
        """
        total = 0
        for msg in messages:
            content = msg.get('content', '')
            total += self.estimate_token_count(content)
            # Add overhead for message structure
            total += 4  # Rough overhead per message
        
        return total
    
    def fits_in_budget(
        self,
        messages: List[Dict[str, str]],
        allow_target_exceed: bool = False
    ) -> bool:
        """
        Check if messages fit within token budget.
        
        Args:
            messages: Messages to check
            allow_target_exceed: If True, allow up to max_tokens; if False, enforce target_tokens
        
        Returns:
            True if messages fit in budget
        """
        estimated = self.estimate_messages_tokens(messages)
        limit = self.max_tokens if allow_target_exceed else self.target_tokens
        
        return (estimated + self.reserve_for_response) <= limit
    
    def prioritize_issues(
        self,
        issues: List[Dict[str, Any]],
        sort_by: str = "severity_complexity"
    ) -> List[Dict[str, Any]]:
        """
        Prioritize issues for processing.
        
        Critical issues first, then by estimated complexity or cost.
        
        Args:
            issues: List of issue dicts
            sort_by: Prioritization method:
                - "severity_complexity": Sort by severity then complexity
                - "severity_only": Sort by severity only
                - "cost": Sort by estimated cost (if available)
                - "category": Group by category
        
        Returns:
            Sorted list of issues
        """
        severity_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "informational": 4,
            "unknown": 5
        }
        
        def get_severity_score(issue: Dict[str, Any]) -> int:
            severity = issue.get('severity', 'unknown').lower()
            return severity_order.get(severity, 5)
        
        def get_complexity_score(issue: Dict[str, Any]) -> int:
            """Estimate complexity based on description length and keywords."""
            description = issue.get('issue', issue.get('description', ''))
            
            # Longer descriptions often indicate more complex issues
            base_score = len(description)
            
            # Keywords that indicate complexity
            complex_keywords = [
                'structural', 'foundation', 'electrical panel', 'replacement',
                'extensive', 'multiple', 'throughout', 'system', 'engineer'
            ]
            
            for keyword in complex_keywords:
                if keyword in description.lower():
                    base_score += 100
            
            return base_score
        
        if sort_by == "severity_complexity":
            issues_sorted = sorted(
                issues,
                key=lambda x: (get_severity_score(x), -get_complexity_score(x))
            )
        elif sort_by == "severity_only":
            issues_sorted = sorted(issues, key=get_severity_score)
        elif sort_by == "cost":
            issues_sorted = sorted(
                issues,
                key=lambda x: -x.get('estimated_cost', x.get('estimated_high', 0))
            )
        elif sort_by == "category":
            issues_sorted = sorted(
                issues,
                key=lambda x: (x.get('category', 'zzz'), get_severity_score(x))
            )
        else:
            issues_sorted = issues
        
        return issues_sorted
    
    def create_batches(
        self,
        issues: List[Dict[str, Any]],
        batch_size: int = 10,
        group_by_category: bool = True
    ) -> List[List[Dict[str, Any]]]:
        """
        Create optimal batches of issues for processing.
        
        Batching reduces API costs but may reduce detail. Best practice:
        - Batch similar issues together (same category)
        - Keep critical issues in smaller batches
        - Limit batch size to maintain quality
        
        Args:
            issues: List of issues to batch
            batch_size: Target issues per batch
            group_by_category: Keep same-category issues together
        
        Returns:
            List of batches (each batch is a list of issues)
        """
        if group_by_category:
            # Group by category first
            category_groups: Dict[str, List[Dict[str, Any]]] = {}
            for issue in issues:
                category = issue.get('category', 'General')
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append(issue)
            
            # Create batches within each category
            batches = []
            for category, category_issues in category_groups.items():
                for i in range(0, len(category_issues), batch_size):
                    batch = category_issues[i:i + batch_size]
                    batches.append(batch)
        else:
            # Simple sequential batching
            batches = []
            for i in range(0, len(issues), batch_size):
                batch = issues[i:i + batch_size]
                batches.append(batch)
        
        self.stats["batches_created"] += len(batches)
        return batches
    
    def optimize_issue_description(
        self,
        issue: Dict[str, Any],
        max_description_length: int = 500
    ) -> Dict[str, Any]:
        """
        Optimize issue description to reduce token usage while preserving key information.
        
        Args:
            issue: Issue dict
            max_description_length: Maximum description length
        
        Returns:
            Issue dict with optimized description
        """
        optimized = issue.copy()
        
        description = issue.get('issue', issue.get('description', ''))
        
        if len(description) > max_description_length:
            # Truncate but try to preserve complete sentences
            truncated = description[:max_description_length]
            last_period = truncated.rfind('.')
            if last_period > max_description_length * 0.7:  # At least 70% preserved
                truncated = truncated[:last_period + 1]
            else:
                truncated += "..."
            
            optimized['issue'] = truncated
            optimized['description'] = truncated
            self.stats["issues_truncated"] += 1
        
        return optimized
    
    def estimate_api_cost(
        self,
        input_tokens: int,
        output_tokens: int = 1000,
        model: str = "gemini-2.5-flash"
    ) -> float:
        """
        Estimate API cost for a request.
        
        Pricing (as of 2025):
        - Gemini 2.5 Flash: $0.075 per 1M input tokens, $0.30 per 1M output tokens
        - GPT-4 Turbo: $10 per 1M input tokens, $30 per 1M output tokens
        
        Args:
            input_tokens: Input token count
            output_tokens: Expected output tokens
            model: Model name
        
        Returns:
            Estimated cost in USD
        """
        pricing = {
            "gemini-2.5-flash": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
            "gemini-pro": {"input": 0.50 / 1_000_000, "output": 1.50 / 1_000_000},
            "gpt-4-turbo": {"input": 10.0 / 1_000_000, "output": 30.0 / 1_000_000},
            "gpt-4": {"input": 30.0 / 1_000_000, "output": 60.0 / 1_000_000},
        }
        
        model_pricing = pricing.get(model, pricing["gemini-2.5-flash"])
        
        input_cost = input_tokens * model_pricing["input"]
        output_cost = output_tokens * model_pricing["output"]
        
        return input_cost + output_cost
    
    def estimate_report_cost(
        self,
        issue_count: int,
        batch_size: int = 1,
        model: str = "gemini-2.5-flash"
    ) -> Dict[str, Any]:
        """
        Estimate total cost to process a full report.
        
        Args:
            issue_count: Number of issues in report
            batch_size: Issues per batch (1 = individual, 10 = batched)
            model: Model name
        
        Returns:
            Dict with cost breakdown
        """
        # Rough token estimates
        system_context_tokens = 1000
        property_context_tokens = 500
        examples_tokens = 2000
        issue_tokens = 300  # Per issue
        output_tokens_per_issue = 250
        
        if batch_size == 1:
            # Individual processing
            api_calls = issue_count
            tokens_per_call = (
                system_context_tokens +
                property_context_tokens +
                examples_tokens +
                issue_tokens
            )
            output_per_call = output_tokens_per_issue
        else:
            # Batch processing
            api_calls = (issue_count + batch_size - 1) // batch_size
            tokens_per_call = (
                system_context_tokens +
                property_context_tokens +
                examples_tokens +
                (issue_tokens * batch_size)
            )
            output_per_call = output_tokens_per_issue * batch_size
        
        total_input_tokens = api_calls * tokens_per_call
        total_output_tokens = api_calls * output_per_call
        
        total_cost = self.estimate_api_cost(
            total_input_tokens,
            total_output_tokens,
            model
        )
        
        return {
            "issue_count": issue_count,
            "batch_size": batch_size,
            "api_calls": api_calls,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "estimated_cost_usd": round(total_cost, 2),
            "cost_per_issue": round(total_cost / issue_count, 4),
            "model": model
        }
    
    def split_large_description(
        self,
        text: str,
        max_chunk_size: int = 2000
    ) -> List[str]:
        """
        Split large text into smaller chunks for processing.
        
        Args:
            text: Text to split
            max_chunk_size: Maximum characters per chunk
        
        Returns:
            List of text chunks
        """
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by sentences
        sentences = text.replace('\n', ' ').split('. ')
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= max_chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics."""
        return {
            **self.stats,
            "max_tokens": self.max_tokens,
            "target_tokens": self.target_tokens,
            "reserve_for_response": self.reserve_for_response
        }
    
    def reset_stats(self):
        """Reset statistics counters."""
        self.stats = {
            "total_issues_processed": 0,
            "total_tokens_estimated": 0,
            "batches_created": 0,
            "issues_truncated": 0
        }

