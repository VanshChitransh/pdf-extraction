"""
Phase 3.2: Group Related Issues
Combines issues that would be fixed together for cost synergies.
"""

from typing import Dict, List, Set
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class IssueGrouper:
    """Groups related issues for cost estimation synergies."""
    
    def __init__(self):
        """Initialize the grouper."""
        self.groups = []
        self.next_group_id = 1
    
    def group_issues(self, issues: List[Dict]) -> List[Dict]:
        """
        Group issues by location, trade, and work type.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Issues with grouping information added
        """
        # Reset groups
        self.groups = []
        self.next_group_id = 1
        
        # Build grouping index
        groups_by_key = defaultdict(list)
        
        for i, issue in enumerate(issues):
            # Get grouping attributes
            locations = issue.get('extracted_attributes', {}).get('locations', [])
            trade = issue.get('classification', {}).get('trade', 'unknown')
            work_type = issue.get('classification', {}).get('work_type', 'unknown')
            category = issue.get('standard_category', 'Unknown')
            
            # Create grouping keys
            # Group 1: Same location + same trade
            if locations:
                for location in locations:
                    key = f"loc_{location}_{trade}"
                    groups_by_key[key].append(i)
            
            # Group 2: Same category + same work type
            key = f"cat_{category}_{work_type}"
            groups_by_key[key].append(i)
            
            # Group 3: Same trade + same work type
            key = f"trade_{trade}_{work_type}"
            groups_by_key[key].append(i)
        
        # Find groups with multiple issues
        issue_to_groups = defaultdict(set)
        
        for key, issue_indices in groups_by_key.items():
            if len(issue_indices) >= 2:  # Only group if 2+ issues
                # Create a group
                group_id = self._create_group(key, issue_indices, issues)
                
                for idx in issue_indices:
                    issue_to_groups[idx].add(group_id)
        
        # Add grouping information to issues
        for i, issue in enumerate(issues):
            if i in issue_to_groups:
                issue['grouped_with'] = list(issue_to_groups[i])
                issue['is_grouped'] = True
            else:
                issue['grouped_with'] = []
                issue['is_grouped'] = False
        
        logger.info(f"Created {len(self.groups)} groups from {len(issues)} issues")
        
        return issues
    
    def _create_group(self, key: str, issue_indices: List[int], issues: List[Dict]) -> str:
        """
        Create a new group.
        
        Args:
            key: Grouping key
            issue_indices: List of issue indices in this group
            issues: Full list of issues
            
        Returns:
            Group ID
        """
        group_id = f"group_{self.next_group_id}"
        self.next_group_id += 1
        
        # Extract group metadata
        group_info = {
            'group_id': group_id,
            'grouping_key': key,
            'issue_count': len(issue_indices),
            'issue_ids': [issues[i].get('id', f'issue_{i}') for i in issue_indices],
            'issue_indices': issue_indices
        }
        
        # Determine group type
        if key.startswith('loc_'):
            group_info['group_type'] = 'location_trade'
        elif key.startswith('cat_'):
            group_info['group_type'] = 'category_work'
        else:
            group_info['group_type'] = 'trade_work'
        
        self.groups.append(group_info)
        
        logger.debug(f"Created {group_id}: {len(issue_indices)} issues, type={group_info['group_type']}")
        
        return group_id
    
    def calculate_cost_adjustment(self, group_size: int, base_cost: float = 1000.0) -> Dict:
        """
        Calculate cost adjustment for grouped issues.
        
        Economies of scale: fixing multiple things together is cheaper per item.
        
        Args:
            group_size: Number of issues in group
            base_cost: Base cost per issue
            
        Returns:
            Dictionary with cost calculations
        """
        if group_size <= 1:
            return {
                'base_cost': base_cost,
                'total_cost': base_cost,
                'adjustment_factor': 1.0,
                'savings': 0.0
            }
        
        # Discount factors based on group size
        # First item: 100%, second: 70%, third+: 60%
        discount_schedule = [1.0, 0.7, 0.6, 0.6, 0.6]
        
        total_cost = base_cost  # First item at full cost
        
        for i in range(1, group_size):
            discount_idx = min(i, len(discount_schedule) - 1)
            total_cost += base_cost * discount_schedule[discount_idx]
        
        # Calculate metrics
        ungrouped_cost = base_cost * group_size
        savings = ungrouped_cost - total_cost
        adjustment_factor = total_cost / ungrouped_cost
        
        return {
            'base_cost_per_item': base_cost,
            'group_size': group_size,
            'total_cost': round(total_cost, 2),
            'ungrouped_cost': round(ungrouped_cost, 2),
            'adjustment_factor': round(adjustment_factor, 3),
            'savings': round(savings, 2),
            'savings_percentage': round((savings / ungrouped_cost) * 100, 1)
        }
    
    def get_groups(self) -> List[Dict]:
        """Get all created groups."""
        return self.groups
    
    def get_group_summary(self) -> Dict:
        """
        Get summary of all groups.
        
        Returns:
            Summary dictionary
        """
        if not self.groups:
            return {
                'total_groups': 0,
                'by_type': {},
                'total_issues_grouped': 0,
                'avg_group_size': 0
            }
        
        by_type = defaultdict(int)
        total_issues = 0
        
        for group in self.groups:
            by_type[group['group_type']] += 1
            total_issues += group['issue_count']
        
        avg_size = total_issues / len(self.groups) if self.groups else 0
        
        return {
            'total_groups': len(self.groups),
            'by_type': dict(by_type),
            'total_issues_grouped': total_issues,
            'avg_group_size': round(avg_size, 1)
        }

