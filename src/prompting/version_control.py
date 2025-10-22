"""
Prompt Version Control

Track, test, and compare different prompt versions to measure improvements
in accuracy, consistency, and confidence.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import hashlib
from pathlib import Path


class PromptVersionControl:
    """
    Manages prompt versions and enables A/B testing.
    
    Features:
    - Log prompts and responses for analysis
    - Compare different prompt versions
    - Track performance metrics
    - Export data for offline analysis
    
    Usage:
        pvc = PromptVersionControl(version_id="v1.0", log_dir="prompt_logs")
        
        # Log a prompt/response pair
        pvc.log_interaction(prompt, response, issue_id, metadata)
        
        # Compare two versions
        comparison = pvc.compare_versions("v1.0", "v1.1", test_issues)
    """
    
    def __init__(
        self,
        version_id: str,
        log_dir: str = "prompt_logs",
        enable_logging: bool = True
    ):
        """
        Initialize version control.
        
        Args:
            version_id: Version identifier (e.g., "v1.0", "v2.0-batch")
            log_dir: Directory to store logs
            enable_logging: Enable/disable logging (disable for production)
        """
        self.version_id = version_id
        self.log_dir = Path(log_dir)
        self.enable_logging = enable_logging
        
        if self.enable_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.version_dir = self.log_dir / version_id
            self.version_dir.mkdir(parents=True, exist_ok=True)
        
        self.interactions = []
        self.metrics = {
            "total_interactions": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "avg_confidence": 0,
            "avg_response_quality": 0,
            "token_usage": 0
        }
    
    def log_interaction(
        self,
        prompt: List[Dict[str, str]],
        response: Optional[Dict[str, Any]],
        issue_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        validation_result: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a prompt/response interaction.
        
        Args:
            prompt: Prompt messages sent to AI
            response: AI response (or None if failed)
            issue_id: Identifier for the issue being estimated
            metadata: Additional metadata (model, temperature, etc.)
            validation_result: Output from OutputValidator
        
        Returns:
            Interaction ID (hash)
        """
        if not self.enable_logging:
            return ""
        
        timestamp = datetime.now().isoformat()
        
        # Create interaction record
        interaction = {
            "interaction_id": self._generate_interaction_id(issue_id, timestamp),
            "version_id": self.version_id,
            "timestamp": timestamp,
            "issue_id": issue_id,
            "prompt": prompt,
            "response": response,
            "metadata": metadata or {},
            "validation_result": validation_result
        }
        
        # Update metrics
        self.metrics["total_interactions"] += 1
        
        if response:
            self.metrics["successful_responses"] += 1
            
            # Update confidence average
            if "confidence_score" in response:
                conf = response["confidence_score"]
                current_avg = self.metrics["avg_confidence"]
                n = self.metrics["successful_responses"]
                self.metrics["avg_confidence"] = (
                    (current_avg * (n - 1) + conf) / n
                )
        else:
            self.metrics["failed_responses"] += 1
        
        if validation_result and "quality_score" in validation_result:
            quality = validation_result["quality_score"]
            current_avg = self.metrics["avg_response_quality"]
            n = self.metrics["successful_responses"]
            if n > 0:
                self.metrics["avg_response_quality"] = (
                    (current_avg * (n - 1) + quality) / n
                )
        
        # Store interaction
        self.interactions.append(interaction)
        
        # Write to file
        self._write_interaction(interaction)
        
        return interaction["interaction_id"]
    
    def log_batch_interaction(
        self,
        prompt: List[Dict[str, str]],
        responses: List[Dict[str, Any]],
        issue_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        validation_results: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Log a batch prompt/response interaction.
        
        Args:
            prompt: Batch prompt messages
            responses: List of AI responses
            issue_ids: List of issue identifiers
            metadata: Additional metadata
            validation_results: List of validation results
        
        Returns:
            List of interaction IDs
        """
        interaction_ids = []
        
        for idx, (response, issue_id) in enumerate(zip(responses, issue_ids)):
            validation = validation_results[idx] if validation_results else None
            batch_metadata = {
                **(metadata or {}),
                "batch_size": len(responses),
                "batch_index": idx
            }
            
            interaction_id = self.log_interaction(
                prompt,
                response,
                issue_id,
                batch_metadata,
                validation
            )
            interaction_ids.append(interaction_id)
        
        return interaction_ids
    
    def get_version_summary(self) -> Dict[str, Any]:
        """Get summary statistics for this version."""
        return {
            "version_id": self.version_id,
            "metrics": self.metrics,
            "interaction_count": len(self.interactions),
            "success_rate": (
                self.metrics["successful_responses"] / self.metrics["total_interactions"]
                if self.metrics["total_interactions"] > 0
                else 0
            )
        }
    
    def compare_versions(
        self,
        other_version_id: str,
        metrics_to_compare: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compare this version with another version.
        
        Args:
            other_version_id: Other version to compare with
            metrics_to_compare: Specific metrics to compare (None = all)
        
        Returns:
            Comparison results
        """
        if not self.enable_logging:
            return {"error": "Logging disabled"}
        
        # Load other version's data
        other_version_dir = self.log_dir / other_version_id
        if not other_version_dir.exists():
            return {"error": f"Version {other_version_id} not found"}
        
        other_metrics = self._load_version_metrics(other_version_id)
        
        # Default metrics to compare
        if metrics_to_compare is None:
            metrics_to_compare = [
                "avg_confidence",
                "avg_response_quality",
                "success_rate",
                "total_interactions"
            ]
        
        comparison = {
            "version_a": self.version_id,
            "version_b": other_version_id,
            "metrics": {}
        }
        
        for metric in metrics_to_compare:
            if metric == "success_rate":
                val_a = (
                    self.metrics["successful_responses"] / self.metrics["total_interactions"]
                    if self.metrics["total_interactions"] > 0
                    else 0
                )
                val_b = (
                    other_metrics["successful_responses"] / other_metrics["total_interactions"]
                    if other_metrics["total_interactions"] > 0
                    else 0
                )
            else:
                val_a = self.metrics.get(metric, 0)
                val_b = other_metrics.get(metric, 0)
            
            comparison["metrics"][metric] = {
                "version_a": val_a,
                "version_b": val_b,
                "difference": val_a - val_b,
                "improvement_percent": (
                    ((val_a - val_b) / val_b * 100) if val_b > 0 else 0
                )
            }
        
        return comparison
    
    def analyze_confidence_distribution(self) -> Dict[str, Any]:
        """Analyze distribution of confidence scores."""
        if not self.interactions:
            return {"error": "No interactions logged"}
        
        confidence_scores = []
        for interaction in self.interactions:
            if interaction["response"] and "confidence_score" in interaction["response"]:
                confidence_scores.append(interaction["response"]["confidence_score"])
        
        if not confidence_scores:
            return {"error": "No confidence scores found"}
        
        # Calculate distribution
        low = sum(1 for s in confidence_scores if s < 50)
        medium = sum(1 for s in confidence_scores if 50 <= s < 70)
        high = sum(1 for s in confidence_scores if 70 <= s < 90)
        very_high = sum(1 for s in confidence_scores if s >= 90)
        
        return {
            "total_responses": len(confidence_scores),
            "distribution": {
                "low (<50)": {"count": low, "percent": low / len(confidence_scores) * 100},
                "medium (50-69)": {"count": medium, "percent": medium / len(confidence_scores) * 100},
                "high (70-89)": {"count": high, "percent": high / len(confidence_scores) * 100},
                "very_high (90+)": {"count": very_high, "percent": very_high / len(confidence_scores) * 100}
            },
            "average": sum(confidence_scores) / len(confidence_scores),
            "min": min(confidence_scores),
            "max": max(confidence_scores)
        }
    
    def analyze_cost_estimates(self) -> Dict[str, Any]:
        """Analyze cost estimate distributions and ranges."""
        if not self.interactions:
            return {"error": "No interactions logged"}
        
        low_estimates = []
        high_estimates = []
        ranges = []
        
        for interaction in self.interactions:
            if interaction["response"]:
                resp = interaction["response"]
                if "estimated_low" in resp and "estimated_high" in resp:
                    low = resp["estimated_low"]
                    high = resp["estimated_high"]
                    low_estimates.append(low)
                    high_estimates.append(high)
                    if low > 0:
                        ranges.append(high / low)
        
        if not low_estimates:
            return {"error": "No cost estimates found"}
        
        return {
            "total_estimates": len(low_estimates),
            "low_estimates": {
                "average": sum(low_estimates) / len(low_estimates),
                "min": min(low_estimates),
                "max": max(low_estimates)
            },
            "high_estimates": {
                "average": sum(high_estimates) / len(high_estimates),
                "min": min(high_estimates),
                "max": max(high_estimates)
            },
            "cost_ranges": {
                "average_ratio": sum(ranges) / len(ranges) if ranges else 0,
                "min_ratio": min(ranges) if ranges else 0,
                "max_ratio": max(ranges) if ranges else 0
            }
        }
    
    def export_interactions(
        self,
        output_file: Optional[str] = None,
        format: str = "json"
    ) -> str:
        """
        Export interactions for analysis.
        
        Args:
            output_file: Output file path (auto-generated if None)
            format: Export format ("json" or "jsonl")
        
        Returns:
            Path to exported file
        """
        if not self.enable_logging:
            return ""
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = str(self.version_dir / f"export_{timestamp}.{format}")
        
        with open(output_file, 'w') as f:
            if format == "jsonl":
                for interaction in self.interactions:
                    f.write(json.dumps(interaction) + "\n")
            else:  # json
                json.dump({
                    "version_id": self.version_id,
                    "metrics": self.metrics,
                    "interactions": self.interactions
                }, f, indent=2)
        
        return output_file
    
    def _generate_interaction_id(self, issue_id: str, timestamp: str) -> str:
        """Generate unique interaction ID."""
        content = f"{self.version_id}:{issue_id}:{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _write_interaction(self, interaction: Dict[str, Any]):
        """Write interaction to file."""
        if not self.enable_logging:
            return
        
        # Write to JSONL file for easy appending
        log_file = self.version_dir / "interactions.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(interaction) + "\n")
        
        # Update metrics file
        metrics_file = self.version_dir / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
    
    def _load_version_metrics(self, version_id: str) -> Dict[str, Any]:
        """Load metrics from another version."""
        metrics_file = self.log_dir / version_id / "metrics.json"
        
        if not metrics_file.exists():
            return {}
        
        with open(metrics_file, 'r') as f:
            return json.load(f)
    
    @classmethod
    def load_version(cls, version_id: str, log_dir: str = "prompt_logs"):
        """
        Load a previously logged version.
        
        Args:
            version_id: Version to load
            log_dir: Log directory
        
        Returns:
            PromptVersionControl instance with loaded data
        """
        pvc = cls(version_id, log_dir, enable_logging=True)
        
        # Load interactions
        interactions_file = pvc.version_dir / "interactions.jsonl"
        if interactions_file.exists():
            with open(interactions_file, 'r') as f:
                for line in f:
                    interaction = json.loads(line)
                    pvc.interactions.append(interaction)
        
        # Load metrics
        metrics_file = pvc.version_dir / "metrics.json"
        if metrics_file.exists():
            with open(metrics_file, 'r') as f:
                pvc.metrics = json.load(f)
        
        return pvc

