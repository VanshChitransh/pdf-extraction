"""
Chunking strategy for efficient API calls.
"""
import logging
from typing import List, Dict, Any
from src.models import InspectionIssue

logger = logging.getLogger(__name__)


class ChunkManager:
    """Manages chunking of issues for batch processing."""
    
    def __init__(
        self,
        max_issues_per_chunk: int = 5,
        max_tokens_per_chunk: int = 8000
    ):
        """
        Initialize chunk manager.
        
        Args:
            max_issues_per_chunk: Maximum issues per API call
            max_tokens_per_chunk: Target token budget per chunk
        """
        self.max_issues_per_chunk = max_issues_per_chunk
        self.max_tokens_per_chunk = max_tokens_per_chunk
        logger.info(f"Initialized ChunkManager: max {max_issues_per_chunk} issues per chunk")
    
    def chunk_issues(
        self,
        issues: List[InspectionIssue],
        strategy: str = "section"
    ) -> List[List[InspectionIssue]]:
        """
        Chunk issues for batch processing.
        
        Args:
            issues: List of issues to chunk
            strategy: Chunking strategy ('section', 'priority', 'simple')
            
        Returns:
            List of issue chunks
        """
        if strategy == "section":
            return self._chunk_by_section(issues)
        elif strategy == "priority":
            return self._chunk_by_priority(issues)
        else:
            return self._chunk_simple(issues)
    
    def _chunk_simple(self, issues: List[InspectionIssue]) -> List[List[InspectionIssue]]:
        """
        Simple chunking: divide into equal-sized chunks.
        
        Args:
            issues: List of issues
            
        Returns:
            List of chunks
        """
        chunks = []
        for i in range(0, len(issues), self.max_issues_per_chunk):
            chunk = issues[i:i + self.max_issues_per_chunk]
            chunks.append(chunk)
        
        logger.info(f"Simple chunking: {len(issues)} issues -> {len(chunks)} chunks")
        return chunks
    
    def _chunk_by_section(self, issues: List[InspectionIssue]) -> List[List[InspectionIssue]]:
        """
        Chunk by section to maintain context.
        
        Args:
            issues: List of issues
            
        Returns:
            List of chunks
        """
        # Group by section
        sections = {}
        for issue in issues:
            section = issue.section
            if section not in sections:
                sections[section] = []
            sections[section].append(issue)
        
        # Create chunks from sections
        chunks = []
        for section_name, section_issues in sections.items():
            # If section has few issues, keep together
            if len(section_issues) <= self.max_issues_per_chunk:
                chunks.append(section_issues)
            else:
                # Split large sections into multiple chunks
                for i in range(0, len(section_issues), self.max_issues_per_chunk):
                    chunk = section_issues[i:i + self.max_issues_per_chunk]
                    chunks.append(chunk)
        
        logger.info(f"Section chunking: {len(issues)} issues -> {len(chunks)} chunks from {len(sections)} sections")
        return chunks
    
    def _chunk_by_priority(self, issues: List[InspectionIssue]) -> List[List[InspectionIssue]]:
        """
        Chunk by priority (high priority first).
        
        Args:
            issues: List of issues
            
        Returns:
            List of chunks
        """
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
        sorted_issues = sorted(
            issues,
            key=lambda x: priority_order.get(x.priority, 999)
        )
        
        # Simple chunk after sorting
        chunks = self._chunk_simple(sorted_issues)
        
        logger.info(f"Priority chunking: {len(issues)} issues -> {len(chunks)} chunks")
        return chunks
    
    def estimate_tokens(self, text: str) -> int:
        """
        Rough estimate of tokens for text.
        Uses approximation: 1 token ≈ 4 characters.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def estimate_chunk_tokens(self, chunk: List[InspectionIssue]) -> int:
        """
        Estimate total tokens for a chunk.
        
        Args:
            chunk: List of issues
            
        Returns:
            Estimated token count
        """
        total = 0
        for issue in chunk:
            # Estimate tokens for each field
            total += self.estimate_tokens(issue.section)
            total += self.estimate_tokens(issue.subsection)
            total += self.estimate_tokens(issue.description)
            total += self.estimate_tokens(issue.title)
        
        # Add overhead for JSON structure and system prompt (~2000 tokens)
        total += 2000
        
        return total
    
    def validate_chunks(self, chunks: List[List[InspectionIssue]]) -> bool:
        """
        Validate that chunks meet size requirements.
        
        Args:
            chunks: List of chunks
            
        Returns:
            True if valid, False otherwise
        """
        for i, chunk in enumerate(chunks):
            if len(chunk) > self.max_issues_per_chunk:
                logger.warning(f"Chunk {i} exceeds max issues: {len(chunk)} > {self.max_issues_per_chunk}")
                return False
            
            tokens = self.estimate_chunk_tokens(chunk)
            if tokens > self.max_tokens_per_chunk:
                logger.warning(f"Chunk {i} exceeds token budget: {tokens} > {self.max_tokens_per_chunk}")
                return False
        
        return True
    
    def get_chunking_stats(self, chunks: List[List[InspectionIssue]]) -> Dict[str, Any]:
        """
        Get statistics about chunks.
        
        Args:
            chunks: List of chunks
            
        Returns:
            Dict with statistics
        """
        chunk_sizes = [len(chunk) for chunk in chunks]
        token_estimates = [self.estimate_chunk_tokens(chunk) for chunk in chunks]
        
        return {
            "total_chunks": len(chunks),
            "total_issues": sum(chunk_sizes),
            "avg_issues_per_chunk": sum(chunk_sizes) / len(chunks) if chunks else 0,
            "min_issues": min(chunk_sizes) if chunk_sizes else 0,
            "max_issues": max(chunk_sizes) if chunk_sizes else 0,
            "estimated_total_tokens": sum(token_estimates),
            "avg_tokens_per_chunk": sum(token_estimates) / len(chunks) if chunks else 0
        }

