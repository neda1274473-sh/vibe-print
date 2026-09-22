"""
Wizard Suggester - Heuristic model suggestions and printing guidance.

Provides minimal but real logic for wizard tools. Not AI — just
structured heuristics based on common 3D printing knowledge.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List

from vibe_print.exceptions import InputValidationError
from vibe_print.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ModelSuggestion:
    """A suggested model type based on user needs."""
    category: str
    template_name: str
    confidence: float
    reason: str
    suggested_parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "template_name": self.template_name,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
            "suggested_parameters": self.suggested_parameters,
        }


@dataclass
class PrintTimeEstimate:
    """Estimated print time and material usage."""
    estimated_time_minutes: float
    estimated_filament_grams: float
    estimated_filament_meters: float
    layer_count: int
    confidence: str
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "estimated_time_minutes": round(self.estimated_time_minutes, 1),
            "estimated_time_hours": round(self.estimated_time_minutes / 60, 2),
            "estimated_filament_grams": round(self.estimated_filament_grams, 1),
            "estimated_filament_meters": round(self.estimated_filament_meters, 2),
            "layer_count": self.layer_count,
            "confidence": self.confidence,
            "notes": self.notes,
        }


@dataclass
class PrinterCompatibilityResult:
    """Result of printer compatibility check."""
    compatible: bool
    model_dimensions_mm: Dict[str, float]
    printer_bed_size_mm: Dict[str, float]
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compatible": self.compatible,
            "model_dimensions_mm": self.model_dimensions_mm,
            "printer_bed_size_mm": self.printer_bed_size_mm,
            "issues": self.issues,
            "warnings": self.warnings,
        }


@dataclass
class PrintingGuide:
    """Step-by-step printing guide for a model category."""
    category: str
    steps: List[Dict[str, str]]
    recommended_material: str
    recommended_preset: str
    tips: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "steps": self.steps,
            "recommended_material": self.recommended_material,
            "recommended_preset": self.recommended_preset,
            "tips": self.tips,
        }


PRINTER_BEDS = {
    "bambu_a1": {"x": 256, "y": 256, "z": 256},
    "bambu_a1_mini": {"x": 180, "y": 180, "z": 180},
    "bambu_p1p": {"x": 256, "y": 256, "z": 256},
    "bambu_x1c": {"x": 256, "y": 256, "z": 256},
    "ender_3": {"x": 220, "y": 220, "z": 250},
    "prusa_mk4": {"x": 250, "y": 210, "z": 220},
}

CATEGORY_KEYWORDS = {
    "tube_squeezer": ["squeezer", "tube", "bottle", "lotion", "toothpaste", "paste", "cream", "squeeze"],
    "holder": ["holder", "stand", "mount", "dock", "cradle", "rest", "phone", "tablet"],
    "bracket": ["bracket", "support", "shelf", "angle", "corner", "brace"],
    "clip": ["clip", "clamp", "catch", "hook", "hanger", "organizer", "cable"],
    "box": ["box", "case", "container", "bin", "tray", "drawer", "storage"],
    "cover": ["cover", "lid", "cap", "protector", "guard", "shield"],
}

CATEGORY_GUIDES = {
    "tube_squeezer": PrintingGuide(
        category="tube_squeezer",
        steps=[
            {"step": "1", "action": "Print with the slot opening facing up", "reason": "Reduces overhangs"},
            {"step": "2", "action": "Use a brim (5-8mm) for bed adhesion", "reason": "Tall narrow parts can warp"},
            {"step": "3", "action": "Set wall loops to 3-4 for strength", "reason": "Withstands squeezing force"},
            {"step": "4", "action": "Test fit with actual tube before full use", "reason": "Clearance may need tuning"},
        ],
        recommended_material="PLA or PETG",
        recommended_preset="tube_squeezer_standard",
        tips=["For heavy-duty use, use PETG", "If slot is too tight, scale up 2-3%"],
    ),
    "holder": PrintingGuide(
        category="holder",
        steps=[
            {"step": "1", "action": "Orient largest flat surface on bed", "reason": "Best adhesion"},
            {"step": "2", "action": "Use supports if angle > 45°", "reason": "Prevents drooping"},
        ],
        recommended_material="PLA",
        recommended_preset="quality",
        tips=["Use TPU for flexible grip", "Add rubber feet to prevent sliding"],
    ),
    "bracket": PrintingGuide(
        category="bracket",
        steps=[
            {"step": "1", "action": "Print mounting holes on bed if possible", "reason": "Best hole accuracy"},
            {"step": "2", "action": "Use 4+ wall loops for load-bearing", "reason": "Strength is critical"},
        ],
        recommended_material="PETG",
        recommended_preset="tube_squeezer_strong",
        tips=["Drill holes after printing for precise fit", "Use heat-set inserts"],
    ),
    "clip": PrintingGuide(
        category="clip",
        steps=[
            {"step": "1", "action": "Use TPU or flexible filament", "reason": "Flexibility prevents breakage"},
            {"step": "2", "action": "Print slowly (30-40mm/s)", "reason": "Better accuracy"},
        ],
        recommended_material="TPU",
        recommended_preset="quality",
        tips=["Test print small section first", "Add chamfers for easier insertion"],
    ),
    "box": PrintingGuide(
        category="box",
        steps=[
            {"step": "1", "action": "Print lid and box separately", "reason": "Better fit"},
            {"step": "2", "action": "Use 3 wall loops for durability", "reason": "Withstands handling"},
        ],
        recommended_material="PLA or PETG",
        recommended_preset="standard",
        tips=["Add text on top layer", "Use grid infill for speed"],
    ),
}


class WizardSuggester:
    """Heuristic model suggester and printing guide provider."""

    def suggest_model(self, description: str) -> List[ModelSuggestion]:
        """Suggest model types based on a natural language description."""
        if not description or not description.strip():
            raise InputValidationError("Description cannot be empty")

        desc_lower = description.lower()
        suggestions = []

        for category, keywords in CATEGORY_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in desc_lower)
            if matches > 0:
                confidence = min(0.95, 0.4 + matches * 0.15)
                params = self._extract_parameters(desc_lower, category)
                suggestions.append(ModelSuggestion(
                    category=category,
                    template_name=category,
                    confidence=confidence,
                    reason=f"Matched {matches} keywords",
                    suggested_parameters=params,
                ))

        suggestions.sort(key=lambda s: s.confidence, reverse=True)

        if not suggestions:
            suggestions.append(ModelSuggestion(
                category="custom",
                template_name="custom_box",
                confidence=0.3,
                reason="No strong keyword match",
                suggested_parameters={},
            ))

        logger.info("Suggested %d models for: %s", len(suggestions), description[:50])
        return suggestions

    def _extract_parameters(self, desc_lower: str, category: str) -> Dict[str, Any]:
        """Extract numeric parameters from description."""
        params: Dict[str, Any] = {}
        dim_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm|millimeter|cm|inch)?', desc_lower)
        if dim_match:
            val = float(dim_match.group(1))
            if 'cm' in desc_lower:
                val *= 10
            params["primary_dimension_mm"] = val
        if any(kw in desc_lower for kw in ["heavy", "strong", "durable", "tough"]):
            params["strength"] = "heavy_duty"
            params["wall_thickness_mm"] = 3.0
        if "tight" in desc_lower:
            params["fit_type"] = "tight"
        elif "loose" in desc_lower or "sliding" in desc_lower:
            params["fit_type"] = "sliding"
        return params

    def estimate_print_time(
        self,
        volume_cm3: float,
        layer_height_mm: float = 0.2,
        infill_density_percent: float = 15.0,
        wall_loops: int = 2,
    ) -> PrintTimeEstimate:
        """Heuristic print time estimation."""
        if volume_cm3 <= 0:
            raise InputValidationError("volume_cm3 must be positive")

        base_speed = 2.5  # cm³/hour at 0.2mm layer, 15% infill
        layer_factor = 0.2 / layer_height_mm  # thinner layers = more time
        infill_factor = 1.0 + (infill_density_percent - 15) / 100
        wall_factor = 1.0 + (wall_loops - 2) * 0.15

        adjusted_speed = base_speed / (layer_factor * infill_factor * wall_factor)
        time_hours = volume_cm3 / adjusted_speed
        time_minutes = time_hours * 60

        # Filament: ~1.24 g/cm³ for PLA, ~330m/kg for 1.75mm
        filament_grams = volume_cm3 * 1.24 * (infill_density_percent / 100 + 0.3)
        filament_meters = filament_grams / 3.0

        layer_count = int(volume_cm3 ** 0.33 * 10 / layer_height_mm)

        notes = [
            f"Based on {volume_cm3:.1f} cm³ volume",
            f"Layer height: {layer_height_mm}mm",
        ]
        if time_minutes > 300:
            notes.append("Long print — consider using draft preset for test")

        return PrintTimeEstimate(
            estimated_time_minutes=time_minutes,
            estimated_filament_grams=filament_grams,
            estimated_filament_meters=filament_meters,
            layer_count=layer_count,
            confidence="medium",
            notes=notes,
        )

    def check_printer_compatibility(
        self,
        model_width_mm: float,
        model_depth_mm: float,
        model_height_mm: float,
        printer_model: str = "bambu_a1",
    ) -> PrinterCompatibilityResult:
        """Check if a model fits on a given printer bed."""
        if printer_model not in PRINTER_BEDS:
            raise InputValidationError(
                f"Unknown printer model: {printer_model}",
                details={"available": list(PRINTER_BEDS.keys())},
            )

        bed = PRINTER_BEDS[printer_model]
        issues: List[str] = []
        warnings: List[str] = []

        if model_width_mm > bed["x"] or model_depth_mm > bed["y"]:
            issues.append(f"Model XY ({model_width_mm}x{model_depth_mm}mm) exceeds bed ({bed['x']}x{bed['y']}mm)")
        if model_height_mm > bed["z"]:
            issues.append(f"Model height ({model_height_mm}mm) exceeds Z limit ({bed['z']}mm)")

        # Warn if close to edge
        if model_width_mm > bed["x"] * 0.9 or model_depth_mm > bed["y"] * 0.9:
            warnings.append("Model is close to bed edge — ensure good bed adhesion")
        if model_height_mm > bed["z"] * 0.8:
            warnings.append("Model is tall — consider slower speeds")

        compatible = len(issues) == 0

        return PrinterCompatibilityResult(
            compatible=compatible,
            model_dimensions_mm={"width": model_width_mm, "depth": model_depth_mm, "height": model_height_mm},
            printer_bed_size_mm=bed,
            issues=issues,
            warnings=warnings,
        )

    def get_printing_guide(self, category: str) -> PrintingGuide:
        """Get printing guide for a model category."""
        if category in CATEGORY_GUIDES:
            return CATEGORY_GUIDES[category]
        # Default generic guide
        return PrintingGuide(
            category=category,
            steps=[
                {"step": "1", "action": "Orient for best bed adhesion", "reason": "Prevents warping"},
                {"step": "2", "action": "Use appropriate supports for overhangs", "reason": "Quality on angled surfaces"},
            ],
            recommended_material="PLA",
            recommended_preset="standard",
            tips=["Start with a small test print", "Check first layer carefully"],
        )
