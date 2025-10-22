"""
Precise Cost Estimator
Improved version with narrower ranges and better parsing.
Uses quantity detection, material analysis, and severity-based multipliers.
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime


class PreciseCostEstimator:
    """More precise cost estimation with narrower ranges (20-40% variance)."""
    
    # Houston market costs with tighter ranges (2024-2025)
    PRECISE_COSTS = {
        # Roofing - more specific
        "roof": {
            "minor_repair": (250, 350, "Minor roof repair (flashing, sealant, small patch)"),
            "moderate_repair": (800, 1200, "Moderate roof repair (several shingles, valley repair)"),
            "section_repair": (1500, 2500, "Section repair (portion of roof)"),
            "major_repair": (4000, 7000, "Major repair (multiple sections, structural)"),
            "full_replacement": (12000, 18000, "Full roof replacement"),
        },
        # Electrical - specific items
        "electrical": {
            "outlet_repair": (100, 175, "Single outlet/switch repair"),
            "multiple_outlets": (300, 500, "Multiple outlets (3-5)"),
            "circuit_repair": (400, 650, "Circuit breaker/wiring repair"),
            "panel_upgrade": (1800, 2500, "Panel upgrade/replacement"),
            "partial_rewire": (3500, 6000, "Partial rewiring (problem areas)"),
            "full_rewire": (8000, 12000, "Full house rewiring"),
        },
        # Plumbing - specific repairs
        "plumbing": {
            "fixture_repair": (150, 300, "Single fixture repair/replacement"),
            "leak_repair": (250, 450, "Leak repair (accessible pipe)"),
            "drain_repair": (400, 700, "Drain line repair"),
            "water_line": (800, 1500, "Water line replacement (section)"),
            "sewer_line": (2500, 4500, "Sewer line repair/replacement"),
            "partial_repipe": (4000, 7000, "Partial repiping (problem areas)"),
        },
        # HVAC - specific components
        "hvac": {
            "service_tune": (120, 220, "Service call/tune-up"),
            "minor_repair": (300, 550, "Minor repair (thermostat, filter, drain)"),
            "component": (600, 1200, "Major component (compressor, coil, motor)"),
            "ductwork": (800, 1500, "Ductwork repair/sealing"),
            "system_replace": (4500, 7500, "Full system replacement"),
        },
        # Foundation - specific levels
        "foundation": {
            "minor_crack": (400, 700, "Minor crack repair/sealing"),
            "moderate": (2500, 4500, "Moderate foundation work (some piers)"),
            "major": (8000, 15000, "Major foundation repair (extensive piers)"),
        },
        # Structural
        "structural": {
            "minor": (400, 800, "Minor structural repair (single joist/beam)"),
            "moderate": (1500, 3000, "Moderate structural repair"),
            "major": (6000, 12000, "Major structural repair"),
        },
        # Exterior
        "exterior": {
            "minor_repair": (200, 400, "Minor exterior repair"),
            "paint_section": (800, 1500, "Paint section/side"),
            "paint_full": (3000, 5000, "Full exterior paint"),
            "siding_repair": (600, 1200, "Siding repair (section)"),
            "siding_replace": (5000, 10000, "Siding replacement (full)"),
        },
        # Interior
        "interior": {
            "cosmetic": (100, 250, "Cosmetic repair"),
            "paint_room": (300, 600, "Paint single room"),
            "drywall_patch": (250, 500, "Drywall patching (minor)"),
            "drywall_major": (800, 1500, "Drywall major repair"),
            "flooring_repair": (600, 1200, "Flooring repair (small area)"),
            "flooring_room": (2000, 4000, "Flooring room replacement"),
        },
        # Windows/Doors
        "windows": {
            "repair": (150, 300, "Window/door repair"),
            "single_replace": (500, 900, "Single window/door replacement"),
            "multiple_2_5": (1500, 3000, "2-5 windows/doors"),
            "multiple_6_10": (3500, 6500, "6-10 windows/doors"),
        },
        # Appliances
        "appliance": {
            "repair": (150, 350, "Appliance repair"),
            "replace": (500, 1200, "Appliance replacement"),
        },
        # Misc
        "misc": {
            "minor": (150, 350, "Minor miscellaneous repair"),
            "moderate": (500, 1000, "Moderate repair"),
            "major": (1500, 3000, "Major repair"),
        }
    }
    
    def __init__(self, precision_mode: str = "balanced"):
        """
        Args:
            precision_mode: "tight" (20% range), "balanced" (30% range), "conservative" (40% range)
        """
        self.precision_mode = precision_mode
        self.stats = {
            "total_issues": 0,
            "estimated_issues": 0,
            "failed_issues": 0,
        }
    
    def estimate_cost(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate cost with improved precision."""
        description = issue.get("description", "").lower()
        issue_type = issue.get("type", "").lower()
        severity = issue.get("severity", "").lower()
        location = issue.get("location", "").lower()
        
        # Parse for quantities and specifics
        quantity = self._extract_quantity(description)
        
        # Classify issue with better granularity
        category, sub_type, confidence = self._classify_precise(
            description, issue_type, severity, location, quantity
        )
        
        # Get base cost
        if category in self.PRECISE_COSTS and sub_type in self.PRECISE_COSTS[category]:
            low, high, reasoning = self.PRECISE_COSTS[category][sub_type]
        else:
            low, high, reasoning = 200, 400, "General repair estimate"
            confidence = max(30, confidence - 20)
        
        # Apply precision mode adjustments
        if self.precision_mode == "tight":
            # Narrow the range to ~20%
            mid = (low + high) / 2
            low = mid * 0.9
            high = mid * 1.1
        elif self.precision_mode == "balanced":
            # Keep original ~30% range
            pass
        else:  # conservative
            # Widen slightly for safety
            low = low * 0.9
            high = high * 1.1
        
        # Adjust for quantity
        if quantity > 1:
            low = low * quantity * 0.85  # bulk discount
            high = high * quantity * 0.90
            reasoning += f" (quantity: {quantity})"
        
        # Add most likely estimate
        most_likely = low * 0.4 + high * 0.6  # weighted toward high
        
        # Build estimate
        estimate = {
            "issue_id": issue.get("issue_id", "unknown"),
            "description": issue.get("description", ""),
            "category": category,
            "sub_type": sub_type,
            "estimated_low": int(low),
            "estimated_most_likely": int(most_likely),
            "estimated_high": int(high),
            "variance_pct": int((high - low) / low * 100),
            "confidence_score": confidence,
            "quantity": quantity if quantity > 1 else None,
            "reasoning": reasoning,
            "assumptions": [
                "Houston market rates (2024-2025)",
                "Includes labor and materials",
                "Standard difficulty access",
                f"Precision mode: {self.precision_mode}"
            ],
            "risk_factors": self._identify_risks(description, severity, confidence),
            "validation": {
                "needs_review": confidence < 70 or (high - low) / low > 0.5,
                "reasoning": self._validation_reason(confidence, high - low, low),
                "is_valid": True
            },
            "metadata": {
                "method": "precise_rule_based",
                "precision_mode": self.precision_mode,
                "generated_at": datetime.now().isoformat()
            }
        }
        
        return estimate
    
    def _extract_quantity(self, description: str) -> int:
        """Extract quantity from description."""
        # Look for quantity indicators
        patterns = [
            r'(\d+)\s*(?:or more|to \d+)',  # "3 to 5", "2 or more"
            r'multiple|several',  # implies 2-3
            r'all|every|throughout',  # implies many
        ]
        
        # Check for explicit numbers
        numbers = re.findall(r'\b(\d+)\b', description)
        if numbers and any(word in description for word in ['window', 'outlet', 'door', 'room']):
            return min(int(numbers[0]), 20)  # cap at 20
        
        # Check for multiplicity words
        if any(word in description for word in ['multiple', 'several']):
            return 3  # assume 3
        
        if any(word in description for word in ['all', 'throughout', 'entire']):
            return 5  # assume 5+
        
        return 1  # single item
    
    def _classify_precise(
        self,
        description: str,
        issue_type: str,
        severity: str,
        location: str,
        quantity: int
    ) -> Tuple[str, str, int]:
        """Classify with better precision."""
        
        confidence = 80  # Higher base confidence
        
        # ROOF - with better specificity
        if any(w in description or w in location for w in 
               ["roof", "shingle", "flashing", "valley", "ridge"]):
            if "replace" in description and any(w in description for w in ["full", "entire", "complete"]):
                return "roof", "full_replacement", 85
            elif any(w in description for w in ["major", "extensive", "structural damage"]):
                return "roof", "major_repair", 80
            elif "section" in description or "portions" in description:
                return "roof", "section_repair", 85
            elif any(w in description for w in ["leak", "damage", "missing", "curled"]):
                return "roof", "moderate_repair", 80
            else:
                return "roof", "minor_repair", 85
        
        # ELECTRICAL - very specific
        if any(w in description or w in location for w in 
               ["electrical", "outlet", "switch", "wiring", "panel", "breaker", "circuit"]):
            if "rewire" in description or "re-wire" in description:
                if "full" in description or "entire" in description:
                    return "electrical", "full_rewire", 75
                else:
                    return "electrical", "partial_rewire", 75
            elif "panel" in description and ("upgrade" in description or "replace" in description):
                return "electrical", "panel_upgrade", 85
            elif "circuit" in description or "breaker" in description:
                return "electrical", "circuit_repair", 80
            elif quantity > 2 or "multiple" in description:
                return "electrical", "multiple_outlets", 80
            else:
                return "electrical", "outlet_repair", 85
        
        # PLUMBING - specific repairs
        if any(w in description or w in location for w in 
               ["plumb", "pipe", "leak", "drain", "water", "sewer"]):
            if "sewer" in description:
                return "plumbing", "sewer_line", 75
            elif "repipe" in description or "re-pipe" in description:
                return "plumbing", "partial_repipe", 70
            elif "water line" in description or "supply line" in description:
                return "plumbing", "water_line", 80
            elif "drain" in description:
                return "plumbing", "drain_repair", 80
            elif "leak" in description:
                return "plumbing", "leak_repair", 85
            else:
                return "plumbing", "fixture_repair", 85
        
        # HVAC - specific components
        if any(w in description or w in location for w in 
               ["hvac", "heating", "cooling", "ac", "air condition", "furnace"]):
            if "replace" in description or "replacement" in description:
                return "hvac", "system_replace", 80
            elif any(w in description for w in ["compressor", "coil", "condenser", "evaporator"]):
                return "hvac", "component", 80
            elif "duct" in description:
                return "hvac", "ductwork", 85
            elif any(w in description for w in ["service", "tune", "maintenance", "no significant"]):
                return "hvac", "service_tune", 85
            else:
                return "hvac", "minor_repair", 80
        
        # FOUNDATION
        if any(w in description or w in location for w in 
               ["foundation", "slab", "pier", "settling"]):
            if "major" in description or "extensive" in description:
                return "foundation", "major", 70
            elif any(w in description for w in ["pier", "leveling", "movement", "differential"]):
                return "foundation", "moderate", 75
            else:
                return "foundation", "minor_crack", 80
        
        # STRUCTURAL
        if any(w in description for w in ["structural", "beam", "joist", "support", "framing"]):
            if "major" in description or "extensive" in description:
                return "structural", "major", 70
            elif "moderate" in description or quantity > 2:
                return "structural", "moderate", 75
            else:
                return "structural", "minor", 80
        
        # EXTERIOR
        if any(w in description or w in location for w in 
               ["exterior", "siding", "stucco", "brick", "fascia", "soffit"]):
            if "siding" in description and ("replace" in description or "replacement" in description):
                if "full" in description or "all" in description:
                    return "exterior", "siding_replace", 75
                else:
                    return "exterior", "siding_repair", 80
            elif "paint" in description:
                if "full" in description or "entire" in description:
                    return "exterior", "paint_full", 80
                else:
                    return "exterior", "paint_section", 80
            else:
                return "exterior", "minor_repair", 85
        
        # WINDOWS/DOORS
        if any(w in description or w in location for w in 
               ["window", "door", "glass", "pane", "seal"]):
            if "replace" in description or "replacement" in description:
                if quantity >= 6:
                    return "windows", "multiple_6_10", 80
                elif quantity >= 2:
                    return "windows", "multiple_2_5", 80
                else:
                    return "windows", "single_replace", 85
            else:
                return "windows", "repair", 85
        
        # INTERIOR
        if any(w in description for w in ["drywall", "ceiling", "wall", "interior"]):
            if "drywall" in description:
                if "major" in description or quantity > 2:
                    return "interior", "drywall_major", 80
                else:
                    return "interior", "drywall_patch", 85
            elif "paint" in description:
                return "interior", "paint_room", 85
            else:
                return "interior", "cosmetic", 85
        
        # FLOORING
        if any(w in description for w in ["floor", "carpet", "tile", "hardwood"]):
            if "room" in description or quantity > 1:
                return "interior", "flooring_room", 75
            else:
                return "interior", "flooring_repair", 80
        
        # APPLIANCES
        if any(w in description for w in ["appliance", "dishwasher", "range", "oven", "microwave", "disposal"]):
            if "replace" in description:
                return "appliance", "replace", 80
            else:
                return "appliance", "repair", 80
        
        # Default based on severity
        if severity in ["critical", "major", "high"]:
            return "misc", "major", 50
        elif severity in ["moderate", "medium"]:
            return "misc", "moderate", 55
        else:
            return "misc", "minor", 60
    
    def _identify_risks(self, description: str, severity: str, confidence: int) -> List[str]:
        """Identify risk factors."""
        risks = []
        
        if confidence < 70:
            risks.append("Low confidence - may need professional evaluation")
        
        if any(w in description.lower() for w in ["hidden", "unknown", "investigate", "further evaluation"]):
            risks.append("May require additional investigation")
        
        if any(w in description.lower() for w in ["structural", "foundation", "load-bearing"]):
            risks.append("May require engineering evaluation")
        
        if any(w in description.lower() for w in ["code", "permit", "violation"]):
            risks.append("May require permits ($100-500 additional)")
        
        if any(w in description.lower() for w in ["water damage", "moisture", "mold"]):
            risks.append("May have related issues requiring additional work")
        
        if not risks:
            risks.append("Standard repair scope")
        
        return risks
    
    def _validation_reason(self, confidence: int, variance: float, low: float) -> str:
        """Generate validation reasoning."""
        variance_pct = (variance / low * 100) if low > 0 else 0
        
        if confidence < 60:
            return "Very low confidence - professional inspection strongly recommended"
        elif confidence < 70:
            return "Low confidence - manual review recommended"
        elif variance_pct > 50:
            return "High variance - scope unclear, may need clarification"
        else:
            return "Standard estimate"
    
    def process_report(
        self,
        enriched_data_path: str,
        output_path: str = None,
        precision_mode: str = None
    ) -> Dict[str, Any]:
        """Process full report with precise estimates."""
        
        if precision_mode:
            self.precision_mode = precision_mode
        
        # Load data
        print(f"Loading enriched data from: {enriched_data_path}")
        with open(enriched_data_path, 'r') as f:
            data = json.load(f)
        
        issues = data.get("issues", [])
        property_data = data.get("property", {})
        
        print(f"Found {len(issues)} issues to estimate")
        print(f"Precision mode: {self.precision_mode}")
        self.stats["total_issues"] = len(issues)
        
        # Generate estimates
        cost_estimates = []
        print("\nGenerating precise cost estimates...")
        
        for idx, issue in enumerate(issues, 1):
            desc_short = issue.get('description', 'Unknown')[:50]
            print(f"[{idx}/{len(issues)}] {desc_short}...", end=" ")
            
            try:
                estimate = self.estimate_cost(issue)
                cost_estimates.append(estimate)
                self.stats["estimated_issues"] += 1
                variance = estimate['variance_pct']
                print(f"✓ ${estimate['estimated_low']}-${estimate['estimated_high']} ({variance}% variance)")
            except Exception as e:
                print(f"✗ Error: {e}")
                self.stats["failed_issues"] += 1
        
        # Calculate summary
        total_low = sum(est["estimated_low"] for est in cost_estimates)
        total_high = sum(est["estimated_high"] for est in cost_estimates)
        total_likely = sum(est["estimated_most_likely"] for est in cost_estimates)
        avg_confidence = sum(est["confidence_score"] for est in cost_estimates) / len(cost_estimates) if cost_estimates else 0
        avg_variance = sum(est["variance_pct"] for est in cost_estimates) / len(cost_estimates) if cost_estimates else 0
        
        # Build results
        results = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "method": "precise_rule_based",
                "precision_mode": self.precision_mode,
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
                "total_estimated_most_likely": int(total_likely),
                "total_estimated_high": int(total_high),
                "total_variance_dollars": int(total_high - total_low),
                "total_variance_pct": int((total_high - total_low) / total_low * 100) if total_low > 0 else 0,
                "average_confidence": int(avg_confidence),
                "average_variance_pct": int(avg_variance),
                "needs_review": sum(1 for est in cost_estimates if est["validation"]["needs_review"])
            },
            "cost_estimates": cost_estimates
        }
        
        # Save results
        if output_path is None:
            output_dir = Path("cost_estimates")
            output_dir.mkdir(exist_ok=True)
            input_name = Path(enriched_data_path).stem.replace("_enriched", "")
            output_path = output_dir / f"{input_name}_precise_estimates.json"
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{'='*70}")
        print("PRECISE COST ESTIMATION SUMMARY")
        print('='*70)
        print(f"Total issues:           {len(issues)}")
        print(f"Successfully estimated: {len(cost_estimates)}")
        print(f"Failed:                 {self.stats['failed_issues']}")
        print(f"Needs review:           {results['summary']['needs_review']}")
        print(f"Average confidence:     {avg_confidence:.0f}%")
        print(f"Average variance:       {avg_variance:.0f}%")
        print()
        print(f"Total cost range:       ${total_low:,.0f} - ${total_high:,.0f}")
        print(f"Most likely total:      ${total_likely:,.0f}")
        print(f"Total variance:         ${total_high - total_low:,.0f} ({(total_high - total_low) / total_low * 100:.0f}%)")
        print('='*70)
        print(f"\n✓ Cost estimates saved to: {output_path}")
        
        return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python precise_cost_estimator.py <enriched_data.json> [tight|balanced|conservative]")
        print()
        print("Precision modes:")
        print("  tight:        ~20% variance (most precise)")
        print("  balanced:     ~30% variance (recommended)")
        print("  conservative: ~40% variance (safety buffer)")
        sys.exit(1)
    
    input_path = sys.argv[1]
    precision_mode = sys.argv[2] if len(sys.argv) > 2 else "balanced"
    
    estimator = PreciseCostEstimator(precision_mode=precision_mode)
    estimator.process_report(input_path)

