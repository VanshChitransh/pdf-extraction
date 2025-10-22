"""
Issue Relationship Analyzer

Analyzes relationships between issues to:
- Find dependencies (one issue causes another)
- Identify bundling opportunities (shared labor/access)
- Detect cascading problems
- Enable more accurate bundled estimates
"""

from typing import Dict, List, Any, Set, Tuple, Optional
from collections import defaultdict


class IssueRelationshipAnalyzer:
    """
    Analyzes relationships between inspection issues.
    
    Usage:
        analyzer = IssueRelationshipAnalyzer()
        
        relationships = analyzer.analyze_all_issues(issues)
        
        bundles = analyzer.group_for_bundled_estimate(
            issue,
            all_issues,
            max_bundle_size=5
        )
    """
    
    def __init__(self):
        """Initialize relationship analyzer."""
        # Define known relationship patterns
        self.causal_relationships = {
            "foundation_cracks": [
                "grading_issues",
                "drainage_problems",
                "plumbing_leaks",
                "door_misalignment",
                "wall_cracks",
                "floor_slope"
            ],
            "roof_leak": [
                "ceiling_stains",
                "attic_moisture",
                "insulation_damage",
                "mold_growth",
                "drywall_damage"
            ],
            "plumbing_leak": [
                "foundation_settlement",
                "water_damage",
                "mold",
                "flooring_damage",
                "ceiling_stains"
            ],
            "hvac_failure": [
                "duct_leaks",
                "thermostat_issues",
                "air_filter_dirty",
                "poor_airflow",
                "high_humidity"
            ],
            "electrical_panel_issues": [
                "frequent_breaker_trips",
                "outlet_problems",
                "flickering_lights",
                "inadequate_power"
            ],
            "drainage_problems": [
                "foundation_issues",
                "basement_moisture",
                "yard_flooding",
                "erosion"
            ],
            "termite_damage": [
                "structural_weakness",
                "wood_deterioration",
                "moisture_problems"
            ]
        }
        
        # Define bundling opportunities (shared access/labor)
        self.bundling_opportunities = {
            "same_location": {
                "description": "Issues in the same physical location",
                "labor_savings": 0.15  # 15% labor savings
            },
            "same_contractor": {
                "description": "Issues requiring the same trade/contractor",
                "labor_savings": 0.20  # 20% savings on setup/mobilization
            },
            "shared_access": {
                "description": "Issues requiring similar access (attic, crawl space, etc.)",
                "labor_savings": 0.25  # 25% savings on access setup
            },
            "related_systems": {
                "description": "Issues in related building systems",
                "labor_savings": 0.10  # 10% efficiency gain
            }
        }
    
    def analyze_all_issues(
        self,
        issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze all issues to find relationships.
        
        Args:
            issues: List of issue dicts from enriched data
        
        Returns:
            Dict with relationship analysis:
            {
                "causal_chains": List of issue chains,
                "bundles": List of bundling opportunities,
                "isolated_issues": List of standalone issues,
                "statistics": Summary stats
            }
        """
        # Filter to only dict issues (skip any malformed entries)
        valid_issues = [issue for issue in issues if isinstance(issue, dict)]
        
        if len(valid_issues) < len(issues):
            print(f"  Warning: Filtered out {len(issues) - len(valid_issues)} non-dict issues")
        
        # Find causal relationships
        causal_chains = self._find_causal_chains(valid_issues)
        
        # Find bundling opportunities
        bundles = self._find_bundling_opportunities(valid_issues)
        
        # Identify isolated issues
        all_related_ids = set()
        for chain in causal_chains:
            all_related_ids.add(self._get_issue_id(chain["root_cause"]))
            all_related_ids.update(self._get_issue_ids(chain["caused_issues"]))
        for bundle in bundles:
            all_related_ids.update(self._get_issue_ids(bundle["issues"]))
        
        isolated = [
            issue for issue in valid_issues
            if self._get_issue_id(issue) not in all_related_ids
        ]
        
        return {
            "causal_chains": causal_chains,
            "bundles": bundles,
            "isolated_issues": isolated,
            "statistics": {
                "total_issues": len(valid_issues),
                "issues_in_chains": len(all_related_ids),
                "isolated_issues": len(isolated),
                "potential_bundles": len(bundles),
                "estimated_savings": self._calculate_potential_savings(bundles)
            }
        }
    
    def group_for_bundled_estimate(
        self,
        primary_issue: Dict[str, Any],
        all_issues: List[Dict[str, Any]],
        max_bundle_size: int = 5
    ) -> Dict[str, Any]:
        """
        Find issues that should be estimated together with primary issue.
        
        Args:
            primary_issue: The main issue being estimated
            all_issues: All issues from the report
            max_bundle_size: Maximum issues in bundle
        
        Returns:
            Bundle information:
            {
                "primary_issue": Dict,
                "related_issues": List[Dict],
                "relationship_type": str,
                "labor_savings_pct": float,
                "bundling_recommendation": str
            }
        """
        # Filter to only valid dict issues
        valid_issues = [i for i in all_issues if isinstance(i, dict)]
        
        primary_id = self._get_issue_id(primary_issue)
        related = []
        
        # Find causally related issues
        causal_related = self._find_caused_issues(primary_issue, valid_issues)
        related.extend(causal_related)
        
        # Find bundling opportunities
        if len(related) < max_bundle_size:
            bundle_related = self._find_bundle_candidates(
                primary_issue,
                valid_issues,
                max_bundle_size - len(related)
            )
            related.extend(bundle_related)
        
        # Remove duplicates and limit size
        seen_ids = {primary_id}
        unique_related = []
        for issue in related:
            issue_id = self._get_issue_id(issue)
            if issue_id not in seen_ids:
                unique_related.append(issue)
                seen_ids.add(issue_id)
                if len(unique_related) >= max_bundle_size:
                    break
        
        # Determine relationship type and savings
        relationship_type, savings_pct = self._determine_bundle_type(
            primary_issue,
            unique_related
        )
        
        # Generate recommendation
        recommendation = self._generate_bundling_recommendation(
            primary_issue,
            unique_related,
            relationship_type,
            savings_pct
        )
        
        return {
            "primary_issue": primary_issue,
            "related_issues": unique_related,
            "relationship_type": relationship_type,
            "labor_savings_pct": savings_pct,
            "bundling_recommendation": recommendation,
            "should_estimate_together": len(unique_related) > 0
        }
    
    def _find_causal_chains(
        self,
        issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find causal chains (one issue causes others)."""
        chains = []
        
        for issue in issues:
            caused_issues = self._find_caused_issues(issue, issues)
            
            if caused_issues:
                chains.append({
                    "root_cause": issue,
                    "caused_issues": caused_issues,
                    "chain_length": len(caused_issues) + 1,
                    "priority": "high" if issue.get("severity", "").lower() in ["critical", "high"] else "medium",
                    "recommendation": f"Address root cause first: {issue.get('item', 'Unknown')}"
                })
        
        return sorted(chains, key=lambda x: x["chain_length"], reverse=True)
    
    def _find_caused_issues(
        self,
        cause_issue: Dict[str, Any],
        all_issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find issues that are likely caused by the given issue."""
        # Safety check
        if not isinstance(cause_issue, dict):
            return []
            
        caused = []
        cause_id = self._get_issue_id(cause_issue)
        
        # Check against known causal relationships
        for cause_pattern, effect_patterns in self.causal_relationships.items():
            if self._matches_pattern(cause_issue, cause_pattern):
                for other_issue in all_issues:
                    if not isinstance(other_issue, dict):
                        continue
                    if self._get_issue_id(other_issue) == cause_id:
                        continue
                    
                    for effect_pattern in effect_patterns:
                        if self._matches_pattern(other_issue, effect_pattern):
                            caused.append(other_issue)
                            break
        
        # Also check for location-based relationships
        cause_location = cause_issue.get("location", "").lower()
        if cause_location:
            for other_issue in all_issues:
                if not isinstance(other_issue, dict):
                    continue
                if self._get_issue_id(other_issue) == cause_id:
                    continue
                
                other_location = other_issue.get("location", "").lower()
                if other_location and cause_location in other_location or other_location in cause_location:
                    # Same location - possible relationship
                    if other_issue not in caused:
                        # Check if plausibly related
                        if self._plausibly_related(cause_issue, other_issue):
                            caused.append(other_issue)
        
        return caused
    
    def _find_bundling_opportunities(
        self,
        issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find opportunities to bundle estimates for efficiency."""
        bundles = []
        
        # Group by location
        location_groups = self._group_by_location(issues)
        for location, group_issues in location_groups.items():
            if len(group_issues) >= 2:
                bundles.append({
                    "bundle_type": "same_location",
                    "location": location,
                    "issues": group_issues,
                    "savings_pct": self.bundling_opportunities["same_location"]["labor_savings"],
                    "reason": f"Multiple issues at {location}"
                })
        
        # Group by contractor type
        contractor_groups = self._group_by_contractor(issues)
        for contractor, group_issues in contractor_groups.items():
            if len(group_issues) >= 2:
                # Check if not already in location bundle
                is_duplicate = any(
                    set(self._get_issue_ids(b["issues"])) == set(self._get_issue_ids(group_issues))
                    for b in bundles
                )
                if not is_duplicate:
                    bundles.append({
                        "bundle_type": "same_contractor",
                        "contractor_type": contractor,
                        "issues": group_issues,
                        "savings_pct": self.bundling_opportunities["same_contractor"]["labor_savings"],
                        "reason": f"All {contractor} work can be scheduled together"
                    })
        
        # Group by access type (attic, crawl space, etc.)
        access_groups = self._group_by_access(issues)
        for access_type, group_issues in access_groups.items():
            if len(group_issues) >= 2:
                is_duplicate = any(
                    set(self._get_issue_ids(b["issues"])) == set(self._get_issue_ids(group_issues))
                    for b in bundles
                )
                if not is_duplicate:
                    bundles.append({
                        "bundle_type": "shared_access",
                        "access_type": access_type,
                        "issues": group_issues,
                        "savings_pct": self.bundling_opportunities["shared_access"]["labor_savings"],
                        "reason": f"All require {access_type} access - setup once"
                    })
        
        return bundles
    
    def _find_bundle_candidates(
        self,
        primary_issue: Dict[str, Any],
        all_issues: List[Dict[str, Any]],
        max_candidates: int
    ) -> List[Dict[str, Any]]:
        """Find issues that should be bundled with primary issue."""
        # Safety check
        if not isinstance(primary_issue, dict):
            return []
            
        candidates = []
        primary_id = self._get_issue_id(primary_issue)
        
        primary_category = primary_issue.get("category", "").lower()
        primary_location = primary_issue.get("location", "").lower()
        primary_contractor = self._infer_contractor_type(primary_issue)
        
        for other_issue in all_issues:
            if not isinstance(other_issue, dict):
                continue
            if self._get_issue_id(other_issue) == primary_id:
                continue
            
            score = 0.0
            
            # Same contractor
            if self._infer_contractor_type(other_issue) == primary_contractor:
                score += 3.0
            
            # Same location
            other_location = other_issue.get("location", "").lower()
            if primary_location and other_location:
                if primary_location == other_location:
                    score += 2.5
                elif primary_location in other_location or other_location in primary_location:
                    score += 1.5
            
            # Same category
            if other_issue.get("category", "").lower() == primary_category:
                score += 2.0
            
            # Similar access requirements
            if self._similar_access(primary_issue, other_issue):
                score += 1.5
            
            if score > 2.0:
                candidates.append((score, other_issue))
        
        # Sort by score and return top candidates
        candidates.sort(reverse=True, key=lambda x: x[0])
        return [issue for score, issue in candidates[:max_candidates]]
    
    def _matches_pattern(self, issue: Dict[str, Any], pattern: str) -> bool:
        """Check if issue matches a pattern."""
        # Safety check
        if not isinstance(issue, dict):
            return False
            
        pattern_words = pattern.lower().replace("_", " ").split()
        
        # Check in multiple fields
        searchable_text = " ".join([
            issue.get("item", ""),
            issue.get("category", ""),
            issue.get("issue", ""),
            issue.get("description", "")
        ]).lower()
        
        # Require at least 2 words to match for multi-word patterns
        if len(pattern_words) > 1:
            matches = sum(1 for word in pattern_words if word in searchable_text)
            return matches >= 2
        else:
            return pattern_words[0] in searchable_text
    
    def _plausibly_related(
        self,
        issue1: Dict[str, Any],
        issue2: Dict[str, Any]
    ) -> bool:
        """Check if two issues are plausibly related."""
        # Water-related issues
        water_keywords = ["leak", "water", "moisture", "stain", "mold", "drainage"]
        issue1_has_water = any(kw in str(issue1.get("issue", "")).lower() for kw in water_keywords)
        issue2_has_water = any(kw in str(issue2.get("issue", "")).lower() for kw in water_keywords)
        
        if issue1_has_water and issue2_has_water:
            return True
        
        # Structural issues
        structural_keywords = ["foundation", "crack", "settlement", "structural", "slope"]
        issue1_structural = any(kw in str(issue1.get("issue", "")).lower() for kw in structural_keywords)
        issue2_structural = any(kw in str(issue2.get("issue", "")).lower() for kw in structural_keywords)
        
        if issue1_structural and issue2_structural:
            return True
        
        return False
    
    def _group_by_location(
        self,
        issues: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group issues by location."""
        groups = defaultdict(list)
        
        for issue in issues:
            location = issue.get("location", "Unknown").strip()
            if location and location.lower() not in ["unknown", "not specified", "n/a"]:
                groups[location].append(issue)
        
        return dict(groups)
    
    def _group_by_contractor(
        self,
        issues: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group issues by contractor type."""
        groups = defaultdict(list)
        
        for issue in issues:
            contractor = self._infer_contractor_type(issue)
            groups[contractor].append(issue)
        
        return dict(groups)
    
    def _group_by_access(
        self,
        issues: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group issues by access type."""
        groups = defaultdict(list)
        
        access_keywords = {
            "attic": ["attic", "roof deck", "soffit"],
            "crawl_space": ["crawl space", "under house", "subfloor"],
            "roof": ["roof", "shingles", "flashing", "gutter"],
            "exterior": ["exterior", "outside", "facade"],
            "basement": ["basement", "below grade"]
        }
        
        for issue in issues:
            searchable = (
                issue.get("location", "") + " " +
                issue.get("issue", "") + " " +
                issue.get("item", "")
            ).lower()
            
            matched = False
            for access_type, keywords in access_keywords.items():
                if any(kw in searchable for kw in keywords):
                    groups[access_type].append(issue)
                    matched = True
                    break
            
            if not matched:
                groups["standard"].append(issue)
        
        return dict(groups)
    
    def _infer_contractor_type(self, issue: Dict[str, Any]) -> str:
        """Infer what type of contractor is needed."""
        # Safety check
        if not isinstance(issue, dict):
            return "unknown"
            
        category = issue.get("category", "").lower()
        item = issue.get("item", "").lower()
        description = issue.get("issue", "").lower()
        
        searchable = f"{category} {item} {description}"
        
        contractor_keywords = {
            "hvac": ["hvac", "air conditioner", "furnace", "heating", "cooling", "duct"],
            "plumber": ["plumbing", "pipe", "drain", "water heater", "leak", "faucet"],
            "electrician": ["electrical", "wiring", "outlet", "panel", "breaker", "switch"],
            "roofer": ["roof", "shingles", "flashing", "gutter", "downspout"],
            "foundation_specialist": ["foundation", "pier", "settlement", "slab"],
            "handyman": ["door", "window", "drywall", "paint", "minor"]
        }
        
        for contractor, keywords in contractor_keywords.items():
            if any(kw in searchable for kw in keywords):
                return contractor
        
        return "general_contractor"
    
    def _similar_access(self, issue1: Dict[str, Any], issue2: Dict[str, Any]) -> bool:
        """Check if issues require similar access."""
        access_indicators = [
            "attic", "crawl space", "roof", "basement",
            "under slab", "behind wall", "exterior"
        ]
        
        text1 = (issue1.get("location", "") + " " + issue1.get("issue", "")).lower()
        text2 = (issue2.get("location", "") + " " + issue2.get("issue", "")).lower()
        
        for indicator in access_indicators:
            if indicator in text1 and indicator in text2:
                return True
        
        return False
    
    def _determine_bundle_type(
        self,
        primary: Dict[str, Any],
        related: List[Dict[str, Any]]
    ) -> Tuple[str, float]:
        """Determine bundle type and savings percentage."""
        if not related:
            return "none", 0.0
        
        # Check for same location
        primary_location = primary.get("location", "").lower()
        same_location = all(
            r.get("location", "").lower() == primary_location
            for r in related if primary_location
        )
        
        if same_location:
            return "same_location", self.bundling_opportunities["same_location"]["labor_savings"]
        
        # Check for same contractor
        primary_contractor = self._infer_contractor_type(primary)
        same_contractor = all(
            self._infer_contractor_type(r) == primary_contractor
            for r in related
        )
        
        if same_contractor:
            return "same_contractor", self.bundling_opportunities["same_contractor"]["labor_savings"]
        
        # Check for similar access
        similar_access = all(
            self._similar_access(primary, r)
            for r in related
        )
        
        if similar_access:
            return "shared_access", self.bundling_opportunities["shared_access"]["labor_savings"]
        
        # Default: related systems
        return "related_systems", self.bundling_opportunities["related_systems"]["labor_savings"]
    
    def _generate_bundling_recommendation(
        self,
        primary: Dict[str, Any],
        related: List[Dict[str, Any]],
        relationship_type: str,
        savings_pct: float
    ) -> str:
        """Generate recommendation text for bundling."""
        if not related:
            return "Estimate independently - no significant bundling opportunities"
        
        savings_display = f"{savings_pct * 100:.0f}%"
        
        recommendations = {
            "same_location": f"Bundle with {len(related)} related issue(s) at same location. Estimated {savings_display} savings on combined labor.",
            "same_contractor": f"Schedule with {len(related)} other {self._infer_contractor_type(primary)} issue(s). Save {savings_display} on mobilization and setup.",
            "shared_access": f"Combine with {len(related)} issue(s) requiring similar access. Save {savings_display} on access setup time.",
            "related_systems": f"Consider addressing with {len(related)} related issue(s) for {savings_display} efficiency gain."
        }
        
        return recommendations.get(
            relationship_type,
            f"Consider bundling with {len(related)} related issue(s)"
        )
    
    def _calculate_potential_savings(
        self,
        bundles: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate potential savings from bundling."""
        return {
            "total_bundles": len(bundles),
            "average_savings_pct": sum(b["savings_pct"] for b in bundles) / len(bundles) if bundles else 0,
            "max_savings_pct": max((b["savings_pct"] for b in bundles), default=0)
        }
    
    def _get_issue_id(self, issue: Dict[str, Any]) -> str:
        """Get unique ID for issue."""
        if not isinstance(issue, dict):
            return "invalid_issue"
        return issue.get("id", f"{issue.get('category', '')}_{issue.get('item', '')}_{issue.get('issue', '')[:20]}")
    
    def _get_issue_ids(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Get IDs for list of issues."""
        return [self._get_issue_id(issue) for issue in issues if isinstance(issue, dict)]

