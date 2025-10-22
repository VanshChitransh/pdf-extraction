"""
Houston-Specific Component Cost Database

Provides structured cost data for common repairs and replacements
with Houston market rates (2024-2025).

Data sources:
- HomeAdvisor Houston market data
- RSMeans construction costs
- Local contractor averages
- Historical project data
"""

from typing import Dict, Any, Optional, Tuple, List
import re


class HoustonCostDatabase:
    """
    Component-level cost lookup with Houston-specific pricing.
    
    Usage:
        db = HoustonCostDatabase()
        
        # Lookup by component
        cost = db.lookup("AC condenser unit", "3 ton")
        
        # Hybrid estimation
        estimate = db.get_estimate("water heater", "50 gallon electric")
    """
    
    def __init__(self):
        """Initialize database with Houston market rates."""
        self.houston_multiplier = 1.12  # Houston is 12% above national average
        
        # Labor rates by trade (Houston average)
        self.labor_rates = {
            "general_contractor": 125,
            "hvac_technician": 125,
            "electrician": 110,
            "plumber": 100,
            "roofer": 85,
            "foundation_specialist": 150,
            "handyman": 65,
            "structural_engineer": 175,
            "pest_control": 75
        }
        
        # Common permit costs (Houston)
        self.permit_costs = {
            "electrical_major": 250,
            "electrical_minor": 150,
            "plumbing_major": 200,
            "plumbing_minor": 100,
            "hvac": 150,
            "roofing": 175,
            "structural": 300,
            "general_repair": 75
        }
        
        # Component cost database (load after labor_rates is defined)
        self.components = self._load_component_data()
    
    def lookup(
        self,
        component: str,
        specifications: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Lookup component cost data.
        
        Args:
            component: Component name (e.g., "AC condenser unit", "water heater")
            specifications: Specifications (e.g., "3 ton", "50 gallon")
            context: Additional context (property_age, access_difficulty, etc.)
        
        Returns:
            Cost data dict or None if not found:
            {
                "component": str,
                "labor_hours": {"min": float, "max": float},
                "labor_rate": float,
                "materials": {"min": float, "max": float},
                "permits": float,
                "additional_costs": Dict,
                "confidence": float (0-1),
                "notes": List[str]
            }
        """
        # Normalize component name
        component_key = self._normalize_component_name(component)
        
        # Find matching component
        for key, data in self.components.items():
            if self._matches_component(component_key, key):
                cost_data = data.copy()
                
                # Apply specifications if provided
                if specifications:
                    cost_data = self._apply_specifications(cost_data, specifications)
                
                # Apply context adjustments
                if context:
                    cost_data = self._apply_context_adjustments(cost_data, context)
                
                return cost_data
        
        return None
    
    def get_estimate(
        self,
        component: str,
        specifications: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get full cost estimate from database lookup.
        
        Args:
            component: Component name
            specifications: Specifications
            context: Additional context
        
        Returns:
            Complete estimate with low/high ranges:
            {
                "estimated_low": float,
                "estimated_high": float,
                "breakdown": {...},
                "confidence": float,
                "notes": List[str]
            }
        """
        cost_data = self.lookup(component, specifications, context)
        
        if not cost_data:
            return None
        
        # Calculate total cost
        labor_low = cost_data["labor_hours"]["min"] * cost_data["labor_rate"]
        labor_high = cost_data["labor_hours"]["max"] * cost_data["labor_rate"]
        
        materials_low = cost_data["materials"]["min"]
        materials_high = cost_data["materials"]["max"]
        
        permits = cost_data.get("permits", 0)
        
        # Additional costs
        additional = sum(cost_data.get("additional_costs", {}).values())
        
        estimated_low = labor_low + materials_low + permits + additional
        estimated_high = labor_high + materials_high + permits + additional
        
        return {
            "estimated_low": round(estimated_low, 2),
            "estimated_high": round(estimated_high, 2),
            "breakdown": {
                "labor": {
                    "low": round(labor_low, 2),
                    "high": round(labor_high, 2),
                    "rate_per_hour": cost_data["labor_rate"],
                    "hours": cost_data["labor_hours"]
                },
                "materials": {
                    "low": round(materials_low, 2),
                    "high": round(materials_high, 2)
                },
                "permits": permits,
                "additional": additional
            },
            "confidence": cost_data.get("confidence", 0.8),
            "contractor_type": cost_data.get("contractor_type", "general_contractor"),
            "notes": cost_data.get("notes", [])
        }
    
    def _load_component_data(self) -> Dict[str, Dict[str, Any]]:
        """Load component cost database."""
        return {
            # === HVAC COMPONENTS ===
            "ac_condenser_unit": {
                "component": "AC Condenser Unit Replacement",
                "contractor_type": "hvac_technician",
                "labor_hours": {"min": 4, "max": 8},
                "labor_rate": self.labor_rates["hvac_technician"],
                "materials": {
                    "2_ton": {"min": 1200, "max": 2500},
                    "3_ton": {"min": 1800, "max": 3500},
                    "4_ton": {"min": 2400, "max": 4500},
                    "5_ton": {"min": 3000, "max": 5500}
                },
                "permits": 150,
                "additional_costs": {
                    "refrigerant": 150,
                    "disposal_fee": 75,
                    "electrical_disconnect": 100
                },
                "confidence": 0.9,
                "notes": [
                    "Houston heat reduces AC lifespan to 10-15 years",
                    "R-410A refrigerant is standard",
                    "Consider full system replacement if unit is 12+ years old"
                ]
            },
            
            "hvac_air_handler": {
                "component": "Air Handler Replacement",
                "contractor_type": "hvac_technician",
                "labor_hours": {"min": 5, "max": 10},
                "labor_rate": self.labor_rates["hvac_technician"],
                "materials": {"min": 1500, "max": 4000},
                "permits": 150,
                "additional_costs": {"ductwork_sealing": 200},
                "confidence": 0.85,
                "notes": [
                    "Includes new thermostat",
                    "Ductwork inspection recommended"
                ]
            },
            
            "hvac_duct_repair": {
                "component": "HVAC Duct Repair/Sealing",
                "contractor_type": "hvac_technician",
                "labor_hours": {"min": 2, "max": 4},
                "labor_rate": self.labor_rates["hvac_technician"],
                "materials": {"min": 150, "max": 400},
                "permits": 0,
                "additional_costs": {},
                "confidence": 0.85,
                "notes": [
                    "Per vent or small section",
                    "Full duct replacement is 10x more expensive"
                ]
            },
            
            # === PLUMBING COMPONENTS ===
            "water_heater": {
                "component": "Water Heater Replacement",
                "contractor_type": "plumber",
                "labor_hours": {"min": 3, "max": 5},
                "labor_rate": self.labor_rates["plumber"],
                "materials": {
                    "40_gallon_gas": {"min": 600, "max": 1200},
                    "50_gallon_gas": {"min": 700, "max": 1400},
                    "40_gallon_electric": {"min": 450, "max": 900},
                    "50_gallon_electric": {"min": 500, "max": 1000},
                    "tankless_gas": {"min": 1200, "max": 2500},
                    "tankless_electric": {"min": 800, "max": 1800}
                },
                "permits": 150,
                "additional_costs": {
                    "pan_and_drain": 100,
                    "expansion_tank": 150,
                    "haul_away": 50
                },
                "confidence": 0.9,
                "notes": [
                    "Houston hard water reduces lifespan to 8-12 years",
                    "Expansion tank required by code",
                    "Tankless may require gas line upgrade"
                ]
            },
            
            "slab_leak_repair": {
                "component": "Under-Slab Plumbing Leak Repair",
                "contractor_type": "plumber",
                "labor_hours": {"min": 8, "max": 16},
                "labor_rate": self.labor_rates["plumber"] * 1.3,  # Premium for slab work
                "materials": {"min": 300, "max": 800},
                "permits": 150,
                "additional_costs": {
                    "concrete_cutting": 400,
                    "leak_detection": 250,
                    "concrete_repair": 350
                },
                "confidence": 0.7,  # High variability
                "notes": [
                    "Very common in Houston slab foundations",
                    "Consider re-routing if multiple leaks",
                    "May require foundation inspection"
                ]
            },
            
            "drain_line_repair": {
                "component": "Drain Line Repair",
                "contractor_type": "plumber",
                "labor_hours": {"min": 2, "max": 6},
                "labor_rate": self.labor_rates["plumber"],
                "materials": {"min": 100, "max": 400},
                "permits": 100,
                "additional_costs": {},
                "confidence": 0.8,
                "notes": [
                    "Pre-1980 Houston homes often have cast iron pipes",
                    "Full replacement recommended if severely corroded"
                ]
            },
            
            # === ELECTRICAL COMPONENTS ===
            "electrical_panel": {
                "component": "Electrical Panel Replacement",
                "contractor_type": "electrician",
                "labor_hours": {"min": 6, "max": 10},
                "labor_rate": self.labor_rates["electrician"],
                "materials": {
                    "100_amp": {"min": 800, "max": 1500},
                    "150_amp": {"min": 1200, "max": 2000},
                    "200_amp": {"min": 1500, "max": 2500}
                },
                "permits": 250,
                "additional_costs": {
                    "meter_base": 200,
                    "ground_rod": 150
                },
                "confidence": 0.9,
                "notes": [
                    "Federal Pacific and Zinsco panels are fire hazards",
                    "200A service recommended for modern homes",
                    "May require utility coordination"
                ]
            },
            
            "gfci_outlet": {
                "component": "GFCI Outlet Installation/Replacement",
                "contractor_type": "electrician",
                "labor_hours": {"min": 0.5, "max": 1},
                "labor_rate": self.labor_rates["electrician"],
                "materials": {"min": 15, "max": 40},
                "permits": 0,
                "additional_costs": {},
                "confidence": 0.95,
                "notes": [
                    "Required in kitchens, bathrooms, outdoors",
                    "Per outlet"
                ]
            },
            
            # === ROOFING COMPONENTS ===
            "shingle_roof_replacement": {
                "component": "Asphalt Shingle Roof Replacement",
                "contractor_type": "roofer",
                "labor_hours_per_square": {"min": 6, "max": 8},  # Per 100 sq ft
                "labor_rate": self.labor_rates["roofer"],
                "materials_per_square": {
                    "3_tab": {"min": 80, "max": 120},
                    "architectural": {"min": 120, "max": 180},
                    "premium": {"min": 180, "max": 300}
                },
                "permits": 175,
                "additional_costs_per_square": {
                    "tear_off": 50,
                    "underlayment": 30,
                    "drip_edge": 15,
                    "ridge_vent": 20
                },
                "confidence": 0.85,
                "notes": [
                    "Hurricane-rated shingles required in Houston",
                    "UV exposure reduces lifespan to 15-20 years",
                    "Full tear-off typically required",
                    "Price is per 100 sq ft (1 'square')"
                ]
            },
            
            "roof_leak_repair": {
                "component": "Roof Leak Repair",
                "contractor_type": "roofer",
                "labor_hours": {"min": 1, "max": 4},
                "labor_rate": self.labor_rates["roofer"],
                "materials": {"min": 50, "max": 200},
                "permits": 0,
                "additional_costs": {},
                "confidence": 0.75,
                "notes": [
                    "Small localized repair",
                    "Multiple leaks may indicate need for replacement"
                ]
            },
            
            # === FOUNDATION COMPONENTS ===
            "foundation_pier": {
                "component": "Foundation Pier Installation",
                "contractor_type": "foundation_specialist",
                "labor_hours_per_pier": {"min": 2, "max": 4},
                "labor_rate": self.labor_rates["foundation_specialist"],
                "materials_per_pier": {
                    "pressed_concrete": {"min": 400, "max": 600},
                    "steel_pier": {"min": 600, "max": 1000},
                    "helical_pier": {"min": 500, "max": 900}
                },
                "permits": 300,
                "additional_costs": {
                    "structural_engineer_report": 800,
                    "soil_test": 400
                },
                "confidence": 0.7,  # High variability
                "notes": [
                    "Houston clay soil requires specialized piers",
                    "Typically need 8-12 piers minimum",
                    "Includes structural engineer evaluation",
                    "Price is per pier"
                ]
            },
            
            "foundation_crack_repair": {
                "component": "Foundation Crack Repair (Minor)",
                "contractor_type": "foundation_specialist",
                "labor_hours": {"min": 2, "max": 4},
                "labor_rate": self.labor_rates["foundation_specialist"],
                "materials": {"min": 100, "max": 300},
                "permits": 0,
                "additional_costs": {
                    "epoxy_injection": 200
                },
                "confidence": 0.75,
                "notes": [
                    "For small cosmetic cracks",
                    "Major cracks require structural evaluation",
                    "May indicate larger foundation issues"
                ]
            },
            
            # === GENERAL REPAIRS ===
            "drywall_repair": {
                "component": "Drywall Repair",
                "contractor_type": "handyman",
                "labor_hours": {"min": 1, "max": 3},
                "labor_rate": self.labor_rates["handyman"],
                "materials": {"min": 20, "max": 75},
                "permits": 0,
                "additional_costs": {
                    "paint_matching": 50
                },
                "confidence": 0.9,
                "notes": [
                    "Small to medium repair (< 4 sq ft)",
                    "Does not include painting full wall"
                ]
            },
            
            "exterior_painting": {
                "component": "Exterior Painting",
                "contractor_type": "general_contractor",
                "labor_per_sqft": {"min": 1.5, "max": 3.0},
                "labor_rate": 45,  # Per hour team rate
                "materials_per_sqft": {"min": 0.5, "max": 1.0},
                "permits": 0,
                "additional_costs_per_job": {
                    "pressure_washing": 300,
                    "minor_wood_repair": 200,
                    "caulking": 150
                },
                "confidence": 0.8,
                "notes": [
                    "Houston humidity requires premium paint",
                    "Preparation is 60% of the job",
                    "Price per square foot"
                ]
            }
        }
    
    def _normalize_component_name(self, component: str) -> str:
        """Normalize component name for matching."""
        normalized = component.lower().strip()
        
        # Remove common words
        remove_words = ["the", "a", "an", "replacement", "repair", "installation"]
        for word in remove_words:
            normalized = normalized.replace(f" {word} ", " ")
            normalized = normalized.replace(f"{word} ", "")
        
        # Normalize spacing
        normalized = " ".join(normalized.split())
        
        return normalized
    
    def _matches_component(self, query: str, database_key: str) -> bool:
        """Check if query matches database key."""
        query_words = set(query.split())
        key_words = set(database_key.replace("_", " ").split())
        
        # Check for significant overlap
        overlap = query_words & key_words
        
        if len(overlap) >= 2:
            return True
        
        # Check for alias matches
        aliases = {
            "ac": ["condenser", "air conditioning", "cooling"],
            "water heater": ["hot water", "heater"],
            "electrical": ["electric", "wiring"],
            "roof": ["roofing", "shingles"],
            "foundation": ["slab", "pier"]
        }
        
        for key, variations in aliases.items():
            if key in query and any(v in database_key for v in variations):
                return True
        
        return False
    
    def _apply_specifications(
        self,
        cost_data: Dict[str, Any],
        specifications: str
    ) -> Dict[str, Any]:
        """Apply specifications to materials cost."""
        spec_lower = specifications.lower()
        
        # Check if materials have variants
        materials = cost_data.get("materials", {})
        
        if isinstance(materials, dict) and any(isinstance(v, dict) for v in materials.values()):
            # Materials have variants (e.g., different sizes)
            for key, value in materials.items():
                if isinstance(value, dict) and any(term in spec_lower for term in key.split("_")):
                    cost_data["materials"] = value
                    cost_data["specification_matched"] = key
                    break
        
        return cost_data
    
    def _apply_context_adjustments(
        self,
        cost_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply context-based adjustments to cost estimate."""
        # Adjust for property age
        property_age = context.get("property_age")
        if property_age and property_age > 30:
            # Older homes often have complications
            cost_data["labor_hours"]["min"] *= 1.1
            cost_data["labor_hours"]["max"] *= 1.2
            cost_data.setdefault("notes", []).append(
                "Older home may have additional complications"
            )
        
        # Adjust for access difficulty
        access_difficulty = context.get("access_difficulty", "normal")
        if access_difficulty == "difficult":
            cost_data["labor_hours"]["min"] *= 1.2
            cost_data["labor_hours"]["max"] *= 1.4
            cost_data.setdefault("notes", []).append(
                "Difficult access increases labor time"
            )
        
        # Adjust confidence based on information quality
        info_quality = context.get("information_quality", "medium")
        if info_quality == "low":
            cost_data["confidence"] *= 0.8
        elif info_quality == "high":
            cost_data["confidence"] = min(0.95, cost_data["confidence"] * 1.1)
        
        return cost_data
    
    def search_components(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for components matching query.
        
        Args:
            query: Search query
        
        Returns:
            List of matching components with relevance scores
        """
        results = []
        query_normalized = self._normalize_component_name(query)
        
        for key, data in self.components.items():
            if self._matches_component(query_normalized, key):
                results.append({
                    "component_key": key,
                    "component_name": data["component"],
                    "contractor_type": data.get("contractor_type", "general_contractor"),
                    "confidence": data.get("confidence", 0.8)
                })
        
        return results
    
    def get_labor_rate(self, contractor_type: str) -> float:
        """Get labor rate for contractor type."""
        return self.labor_rates.get(contractor_type, self.labor_rates["general_contractor"])
    
    def get_permit_cost(self, permit_type: str) -> float:
        """Get permit cost for type."""
        return self.permit_costs.get(permit_type, 100)

