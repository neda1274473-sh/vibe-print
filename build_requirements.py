#!/usr/bin/env python3
"""Build the new requirements.py file."""

OUTPUT = r'''"""Requirements Parser - Extract structured parameters from natural language."""
import json, re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple

class ObjectCategory(str, Enum):
    BOX = "box"
    CYLINDER = "cylinder"
    TUBE_SQUEEZER = "tube_squeezer"
    BRACKET = "bracket"
    ENCLOSURE = "enclosure"
    SPACER = "spacer"
    HOOK = "hook"
    CUP_HOLDER = "cup_holder"
    PHONE_STAND = "phone_stand"
    KEYCHAIN = "keychain"
    CABLE_CLIP = "cable_clip"
    CUSTOM = "custom"

class FitType(str, Enum):
    TIGHT = "tight"
    SNUG = "snug"
    SLIDING = "sliding"
    LOOSE = "loose"

@dataclass
class Dimension:
    value: float
    unit: str = "mm"
    context: str = ""
    is_target: bool = True

    def to_mm(self) -> float:
        conversions = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4, "inch": 25.4, "inches": 25.4, "ft": 304.8}
        return self.value * conversions.get(self.unit.lower(), 1.0)

@dataclass
class ModelRequirements:
    name: str = ""
    description: str = ""
    category: ObjectCategory = ObjectCategory.CUSTOM
    target_dimensions: List[Dimension] = field(default_factory=list)
    max_dimensions: Optional[Tuple[float, float, float]] = None
    fit_type: FitType = FitType.SLIDING
    needs_strength: bool = False
    needs_flexibility: bool = False
    needs_water_resistance: bool = False
    wall_thickness_mm: float = 2.0
    corner_radius_mm: float = 1.0
    add_grip_texture: bool = False
    reference_object: str = ""
    similar_to: str = ""
    original_text: str = ""
    extracted_numbers: List[float] = field(default_factory=list)
    confidence_score: float = 0.0
    top_candidates: List[Tuple[str, float]] = field(default_factory=list)
    clarification_needed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "target_dimensions": [
                {"value": d.value, "unit": d.unit, "context": d.context, "mm": d.to_mm()}
                for d in self.target_dimensions
            ],
            "max_dimensions_mm": self.max_dimensions,
            "fit_type": self.fit_type.value,
            "needs_strength": self.needs_strength,
            "wall_thickness_mm": self.wall_thickness_mm,
            "reference_object": self.reference_object,
            "similar_to": self.similar_to,
            "confidence_score": self.confidence_score,
            "top_candidates": self.top_candidates,
            "clarification_needed": self.clarification_needed,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def get_primary_dimension_mm(self) -> Optional[float]:
        if self.target_dimensions:
            return self.target_dimensions[0].to_mm()
        return None


@dataclass
class CategoryScore:
    category: ObjectCategory
    raw_score: float
    matched_keywords: List[str]
    penalized: bool
    penalty_reason: str = ""


class RequirementsParser:
    """
    Parses natural language requirements into structured ModelRequirements.

    Uses a context-aware scoring system with:
    - Multi-word phrase boosting (specific phrases dominate generic words)
    - Explicit negative/exclusion signals (co-occurring words can block categories)
    - Confidence thresholding (low-confidence requests trigger clarification)
    """

    CONFIDENCE_THRESHOLD = 5.0
    """Minimum score required to accept a category match without asking
    for clarification. Below this, the system returns CUSTOM with top
    candidates listed."""

    DIMENSION_PATTERNS = [
        r'(\d+\.?\d*)\s*(mm|cm|in|inch|inches?)\s*(diameter|wide|tall|long|thick|deep)?',
        r'(\d+\.?\d*)\s*(inches?|in|cm|mm)\s*(wide|tall|long|thick|deep|diameter)?',
        r'(diameter|width|height|length|thickness)\s*(?:of|:|\s)\s*(\d+\.?\d*)\s*(mm|cm|in)?',
        r'(\d+\.?\d*)\s*(oz|fl\s*oz|ml|liter|L)\s*(bottle|container|tube)?',
    ]

    # Each entry: (keyword, weight, is_phrase)
    # Phrases get 2x multiplier. Single generic words have LOW weights.
    CATEGORY_KEYWORDS = {
        ObjectCategory.TUBE_SQUEEZER: [
            ("tube squeezer", 8.0, True),
            ("toothpaste squeezer", 8.0, True),
            ("lotion squeezer", 8.0, True),
            ("squeezer", 4.0, False),
            ("squeeze", 3.0, False),
            ("toothpaste", 3.0, False),
            ("lotion", 3.0, False),
            ("cream", 2.0, False),
            ("paste", 2.0, False),
            ("dispenser", 2.0, False),
            ("roller", 2.0, False),
            ("wringer", 2.0, False),
        ],
        ObjectCategory.BRACKET: [
            ("monitor stand", 8.0, True),
            ("shelf bracket", 8.0, True),
            ("wall mount", 6.0, True),
            ("corner brace", 6.0, True),
            ("l bracket", 6.0, True),
            ("l-shaped", 5.0, True),
            ("bracket", 5.0, False),
            ("mounting", 3.0, False),
            ("mount", 2.0, False),
            ("stand", 1.5, False),
            ("brace", 3.0, False),
        ],
        ObjectCategory.ENCLOSURE: [
            ("electronics box", 8.0, True),
            ("project box", 8.0, True),
            ("raspberry pi", 7.0, True),
            ("arduino", 6.0, False),
            ("compartment", 4.0, False),
            ("cavity", 4.0, False),
            ("enclosure", 6.0, False),
            ("housing", 5.0, False),
            ("case", 3.0, False),
            ("container", 3.0, False),
            ("hollow", 4.0, False),
            ("lid", 3.0, False),
            ("storing", 3.0, False),
            ("inside", 2.0, False),
            ("shell", 3.0, False),
            ("cover", 2.0, False),
        ],
        ObjectCategory.BOX: [
            ("rectangular prism", 8.0, True),
            ("calibration cube", 8.0, True),
            ("test cube", 8.0, True),
            ("solid block", 6.0, True),
            ("solid box", 6.0, True),
            ("no lid", 5.0, True),
            ("box", 4.0, False),
        ],
        ObjectCategory.CYLINDER: [
            ("cylindrical rod", 7.0, True),
            ("round rod", 6.0, True),
            ("cylinder", 5.0, False),
            ("rod", 3.0, False),
            ("peg", 3.0, False),
            ("disc", 3.0, False),
            ("disk", 3.0, False),
            ("pin", 3.0, False),
            ("shaft", 3.0, False),
            ("round", 2.0, False),
            ("tube", 2.0, False),
        ],
        ObjectCategory.SPACER: [
            ("spacer washer", 7.0, True),
            ("spacer ring", 7.0, True),
            ("standoff", 6.0, False),
            ("bushing", 5.0, False),
            ("grommet", 5.0, False),
            ("spacer", 5.0, False),
            ("washer", 4.0, False),
            ("pcb", 2.0, False),
        ],
        ObjectCategory.HOOK: [
            ("wall hook", 7.0, True),
            ("coat hook", 7.0, True),
            ("hook", 5.0, False),
            ("hanger", 4.0, False),
            ("clip", 1.5, False),
            ("clamp", 2.0, False),
            ("grip", 2.0, False),
            ("grabber", 2.0, False),
        ],
        ObjectCategory.CUP_HOLDER: [
            ("cup holder", 10.0, True),
            ("drink holder", 8.0, True),
            ("can holder", 8.0, True),
            ("bottle holder", 7.0, True),
            ("cup", 4.0, False),
            ("mug", 4.0, False),
            ("can", 3.0, False),
            ("beverage", 3.0, False),
        ],
        ObjectCategory.PHONE_STAND: [
            ("phone stand", 10.0, True),
            ("phone holder", 8.0, True),
            ("mobile stand", 8.0, True),
            ("smartphone stand", 9.0, True),
            ("cell phone stand", 9.0, True),
            ("phone dock", 7.0, True),
            ("phone cradle", 7.0, True),
            ("phone", 3.0, False),
            ("smartphone", 3.0, False),
        ],
        ObjectCategory.KEYCHAIN: [
            ("keychain", 10.0, False),
            ("key chain", 10.0, True),
            ("key ring", 8.0, True),
            ("key fob", 8.0, True),
            ("key tag", 7.0, True),
            ("key holder", 7.0, True),
            ("keyring", 8.0, False),
            ("key", 2.0, False),
        ],
        ObjectCategory.CABLE_CLIP: [
            ("cable clip", 10.0, True),
            ("cable holder", 8.0, True),
            ("wire clip", 9.0, True),
            ("cord clip", 9.0, True),
            ("cable organizer", 7.0, True),
            ("cable management", 7.0, True),
            ("usb clip", 8.0, True),
            ("cable", 3.0, False),
            ("wire", 3.0, False),
            ("cord", 3.0, False),
        ],
    }

    # Exclusion rules: (blocking_words, blocked_category, penalty)
    EXCLUSION_RULES = [
        (["phone", "smartphone", "cell phone"