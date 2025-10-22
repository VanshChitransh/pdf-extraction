"""
Rule-Based Cost Estimator
Provides cost estimates based on industry standards and typical repair costs.
Useful as a fallback when AI API is unavailable or rate-limited.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class RuleBasedCostEstimator:
    """Estimate repair costs using rule-based logic and typical cost ranges."""
    
    # Houston market typical costs (2024-2025)
    COST_DATABASE = {
        # Roofing
        "roof": {
            "minor": (200, 500, "Minor roof repair (flashing, sealant)"),
            "moderate": (500, 2000, "Moderate roof repair (shingles, valleys)"),
            "major": (2000, 8000, "Major roof repair or section replacement"),
            "replacement": (8000, 25000, "Full roof replacement"),
        },
        # Electrical
        "electrical": {
            "outlet": (100, 250, "Outlet/switch repair or replacement"),
            "circuit": (300, 800, "Circuit repair or breaker replacement"),
            "panel": (1500, 3000, "Electrical panel upgrade"),
            "rewire": (3000, 10000, "Partial or full rewiring"),
        },
        # Plumbing
        "plumbing": {
            "minor": (150, 400, "Minor plumbing repair (leak, fixture)"),
            "moderate": (400, 1500, "Moderate plumbing (pipe replacement, drain)"),
            "major": (1500, 5000, "Major plumbing (re-pipe, sewer line)"),
        },
        # HVAC
        "hvac": {
            "service": (100, 300, "HVAC service or minor repair"),
            "component": (300, 1000, "Component replacement (compressor, fan)"),
            "replacement": (3000, 8000, "Full HVAC system replacement"),
        },
        # Foundation
        "foundation": {
            "minor": (500, 2000, "Minor foundation repair (cracks, settling)"),
            "moderate": (2000, 8000, "Moderate foundation repair (piers, leveling)"),
            "major": (8000, 30000, "Major foundation repair or stabilization"),
        },
        # Structural
        "structural": {
            "minor": (300, 1000, "Minor structural repair (joist, beam)"),
            "moderate": (1000, 5000, "Moderate structural repair"),
            "major": (5000, 20000, "Major structural repair or reinforcement"),
        },
        # Exterior
        "exterior": {
            "minor": (200, 800, "Minor exterior repair (siding, trim)"),
            "paint": (2000, 5000, "Exterior painting"),
            "siding": (3000, 12000, "Siding replacement"),
        },
        # Interior
        "interior": {
            "cosmetic": (100, 500, "Cosmetic repair (paint, patch)"),
            "flooring": (1000, 5000, "Flooring repair or replacement"),
            "drywall": (300, 1500, "Drywall repair"),
        },
        # Windows/Doors
        "windows": {
            "repair": (100, 400, "Window/door repair"),
            "replacement": (400, 1200, "Single window/door replacement"),
            "multiple": (2000, 8000, "Multiple windows/doors replacement"),
        },
        # Miscellaneous
        "misc": {
            "minor": (100, 500, "Minor repair"),
            "moderate": (500, 2000, "Moderate repair"),
            "major": (2000, 8000, "Major repair"),
        }
    }
    
    def __init__(self):
        self.stats = {
            "total_issues": 0,
            "estimated_issues": 0,
            "failed_issues": 0,
        }
    
    def estimate_cost(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate cost for a single issue using rule-based logic.
        
        Args:
            issue: Issue data with description, severity, location, etc.
            
        Returns:
            Cost estimate dictionary
        """
        # Extract issue details
        description = issue.get("description", "").lower()
        issue_type = issue.get("type", "").lower()
        severity = issue.get("severity", "").lower()
        location = issue.get("location", "").lower()
        
        # Determine category and severity
        category, sub_type, confidence = self._classify_issue(
            description, issue_type, severity, location
        )
        
        # Get cost range
        if category in self.COST_DATABASE and sub_type in self.COST_DATABASE[category]:
            low, high, reasoning = self.COST_DATABASE[category][sub_type]
        else:
            # Default fallback
            low, high, reasoning = 200, 1000, "General repair estimate"
            confidence = max(30, confidence - 20)
        
        # Adjust based on severity
        low, high = self._adjust_for_severity(low, high, severity)
        
        # Build estimate
        estimate = {
            "issue_id": issue.get("issue_id", "unknown"),
            "description": issue.get("description", ""),
            "category": category,
            "sub_type": sub_type,
            "estimated_low": int(low),
            "estimated_high": int(high),
            "confidence_score": confidence,
            "reasoning": reasoning,
            "assumptions": [
                "Based on Houston market rates (2024-2025)",
                "Includes labor and materials",
                "Assumes standard difficulty access",
                "May vary based on contractor and scope"
            ],
            "risk_factors": self._identify_risks(description, severity),
            "validation": {
                "needs_review": confidence < 70,
                "reasoning": "Low confidence estimate" if confidence < 70 else "Standard estimate",
                "is_valid": True
            },
            "metadata": {
                "method": "rule_based",
                "generated_at": datetime.now().isoformat()
            }
        }
        
        return estimate
    
    def _classify_issue(
        self, 
        description: str, 
        issue_type: str, 
        severity: str, 
        location: str
    ) -> tuple:
        """Classify issue into category and sub-type."""
        
        confidence = 75  # Base confidence for rule-based
        
        # Roof-related
        if any(word in description or word in location for word in 
               ["roof", "shingle", "flashing", "valley", "ridge", "soffit", "fascia"]):
            if "replace" in description or "replacement" in description:
                return "roof", "replacement", 85
            elif any(word in description for word in ["major", "extensive", "structural"]):
                return "roof", "major", 80
            elif any(word in description for word in ["leak", "damage", "missing"]):
                return "roof", "moderate", 75
            else:
                return "roof", "minor", 70
        
        # Electrical
        if any(word in description or word in location for word in 
               ["electrical", "outlet", "switch", "wiring", "panel", "breaker", "gfci", "circuit"]):
            if "panel" in description or "upgrade" in description:
                return "electrical", "panel", 80
            elif any(word in description for word in ["rewire", "re-wire", "wiring"]):
                return "electrical", "rewire", 75
            elif "circuit" in description or "breaker" in description:
                return "electrical", "circuit", 80
            else:
                return "electrical", "outlet", 75
        
        # Plumbing
        if any(word in description or word in location for word in 
               ["plumb", "pipe", "leak", "drain", "water", "sewer", "faucet", "toilet", "sink"]):
            if any(word in description for word in ["sewer", "main", "repipe", "re-pipe"]):
                return "plumbing", "major", 70
            elif any(word in description for word in ["extensive", "multiple", "throughout"]):
                return "plumbing", "moderate", 75
            else:
                return "plumbing", "minor", 80
        
        # HVAC
        if any(word in description or word in location for word in 
               ["hvac", "heating", "cooling", "ac", "furnace", "air condition", "compressor"]):
            if "replace" in description or "replacement" in description:
                return "hvac", "replacement", 80
            elif any(word in description for word in ["compressor", "coil", "fan motor"]):
                return "hvac", "component", 75
            else:
                return "hvac", "service", 80
        
        # Foundation
        if any(word in description or word in location for word in 
               ["foundation", "slab", "pier", "settling", "structural crack"]):
            if any(word in description for word in ["major", "extensive", "structural"]):
                return "foundation", "major", 70
            elif any(word in description for word in ["pier", "leveling", "settlement"]):
                return "foundation", "moderate", 75
            else:
                return "foundation", "minor", 70
        
        # Structural
        if any(word in description or word in location for word in 
               ["structural", "beam", "joist", "support", "load-bearing"]):
            if "major" in description or "extensive" in description:
                return "structural", "major", 70
            elif "moderate" in description:
                return "structural", "moderate", 75
            else:
                return "structural", "minor", 75
        
        # Exterior
        if any(word in description or word in location for word in 
               ["siding", "exterior", "trim", "paint", "stucco", "brick"]):
            if "siding" in description and "replace" in description:
                return "exterior", "siding", 75
            elif "paint" in description:
                return "exterior", "paint", 80
            else:
                return "exterior", "minor", 75
        
        # Windows/Doors
        if any(word in description or word in location for word in 
               ["window", "door", "glass", "frame", "seal"]):
            if "replace" in description or "replacement" in description:
                if "multiple" in description or "all" in description:
                    return "windows", "multiple", 75
                else:
                    return "windows", "replacement", 80
            else:
                return "windows", "repair", 80
        
        # Interior/Cosmetic
        if any(word in description or word in location for word in 
               ["paint", "drywall", "wall", "ceiling", "cosmetic"]):
            if "drywall" in description:
                return "interior", "drywall", 80
            else:
                return "interior", "cosmetic", 75
        
        # Flooring
        if any(word in description or word in location for word in 
               ["floor", "carpet", "tile", "hardwood", "laminate"]):
            return "interior", "flooring", 75
        
        # Default fallback
        if severity in ["critical", "major", "high"]:
            return "misc", "major", 50
        elif severity in ["moderate", "medium"]:
            return "misc", "moderate", 50
        else:
            return "misc", "minor", 50
    
    def _adjust_for_severity(self, low: float, high: float, severity: str) -> tuple:
        """Adjust cost range based on severity."""
        if severity in ["critical", "major"]:
            return low * 1.3, high * 1.5
        elif severity in ["moderate", "medium"]:
            return low * 1.0, high * 1.2
        else:
            return low * 0.8, high * 1.0
    
    def _identify_risks(self, description: str, severity: str) -> List[str]:
        """Identify potential risk factors."""
        risks = []
        
        if severity in ["critical", "major", "high"]:
            risks.append("High priority issue - costs may escalate if delayed")
        
        if any(word in description.lower() for word in ["hidden", "unknown", "investigate"]):
            risks.append("May require additional investigation")
        
        if any(word in description.lower() for word in ["structural", "foundation", "load"]):
            risks.append("May require engineering evaluation")
        
        if any(word in description.lower() for word in ["code", "permit", "violation"]):
            risks.append("May require permits and inspections")
        
        if any(word in description.lower() for word in ["water", "moisture", "mold"]):
            risks.append("May have related water damage or mold issues")
        
        if not risks:
            risks.append("Standard repair with typical scope")
        
        return risks
    
    def process_report(self, enriched_data_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Process full report and generate cost estimates.
        
        Args:
            enriched_data_path: Path to enriched data JSON
            output_path: Path for output (auto-generated if None)
            
        Returns:
            Complete cost estimation results
        """
        # Load data
        print(f"Loading enriched data from: {enriched_data_path}")
        with open(enriched_data_path, 'r') as f:
            data = json.load(f)
        
        issues = data.get("issues", [])
        property_data = data.get("property", {})
        
        print(f"Found {len(issues)} issues to estimate")
        self.stats["total_issues"] = len(issues)
        
        # Generate estimates
        cost_estimates = []
        print("\nGenerating rule-based cost estimates...")
        
        for idx, issue in enumerate(issues, 1):
            print(f"[{idx}/{len(issues)}] {issue.get('description', 'Unknown')[:60]}...", end=" ")
            
            try:
                estimate = self.estimate_cost(issue)
                cost_estimates.append(estimate)
                self.stats["estimated_issues"] += 1
                print(f"✓ ${estimate['estimated_low']}-${estimate['estimated_high']}")
            except Exception as e:
                print(f"✗ Error: {e}")
                self.stats["failed_issues"] += 1
        
        # Calculate summary
        total_low = sum(est["estimated_low"] for est in cost_estimates)
        total_high = sum(est["estimated_high"] for est in cost_estimates)
        avg_confidence = sum(est["confidence_score"] for est in cost_estimates) / len(cost_estimates) if cost_estimates else 0
        
        # Build results
        results = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "method": "rule_based",
                "property_data": {
                    "year_built": property_data.get("year_built", "Unknown"),
                    "type": property_data.get("type", "Unknown"),
                    "square_footage": property_data.get("square_footage", "Unknown"),
                    "location": "Houston, TX",
                    "inspection_date": property_data.get("inspection_date", "Unknown"),
                }
            },
            "summary": {
                "total_issues": len(issues),
                "estimated_issues": len(cost_estimates),
                "failed_issues": self.stats["failed_issues"],
                "total_estimated_low": int(total_low),
                "total_estimated_high": int(total_high),
                "average_confidence": int(avg_confidence),
                "needs_review": sum(1 for est in cost_estimates if est["validation"]["needs_review"])
            },
            "cost_estimates": cost_estimates
        }
        
        # Save results
        if output_path is None:
            output_dir = Path("cost_estimates")
            output_dir.mkdir(exist_ok=True)
            input_name = Path(enriched_data_path).stem.replace("_enriched", "")
            output_path = output_dir / f"{input_name}_cost_estimates.json"
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{'='*70}")
        print("RULE-BASED COST ESTIMATION SUMMARY")
        print('='*70)
        print(f"Total issues:           {len(issues)}")
        print(f"Successfully estimated: {len(cost_estimates)}")
        print(f"Failed:                 {self.stats['failed_issues']}")
        print(f"Needs review:           {results['summary']['needs_review']}")
        print(f"Average confidence:     {avg_confidence:.0f}%")
        print(f"Total cost range:       ${total_low:,.0f} - ${total_high:,.0f}")
        print('='*70)
        print(f"\n✓ Cost estimates saved to: {output_path}")
        
        return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python rule_based_cost_estimator.py <enriched_data.json> [output.json]")
        sys.exit(1)
    
    estimator = RuleBasedCostEstimator()
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    estimator.process_report(input_path, output_path)

