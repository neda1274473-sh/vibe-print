import textwrap

content = textwrap.dedent(r'''
"""Requirements Parser - Extract structured parameters from natural language."""
import json, re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple

class ObjectCategory(str, Enum):
    BOX="box"; CYLINDER="cylinder"; TUBE_SQUEEZER="tube_squeezer"; BRACKET="bracket"
    ENCLOSURE="enclosure"; SPACER="spacer"; HOOK="hook"; CUP_HOLDER="cup_holder"
    PHONE_STAND="phone_stand"; KEYCHAIN="keychain"; CABLE_CLIP="cable_clip"; CUSTOM="custom"

class FitType(str, Enum):
    TIGHT="tight"; SNUG="snug"; SLIDING="sliding"; LOOSE="loose"

@dataclass
class Dimension:
    value: float; unit: str="mm"; context: str=""; is_target: bool=True
    def to_mm(self):
        c={"mm":1.0,"cm":10.0,"m":1000.0,"in":25.4,"inch":25.4,"inches":25.4,"ft":304.8}
        return self.value*c.get(self.unit.lower(),1.0)

@dataclass
class ModelRequirements:
    name: str=""; description: str=""; category: ObjectCategory=ObjectCategory.CUSTOM
    target_dimensions: List[Dimension]=field(default_factory=list)
    max_dimensions: Optional[Tuple[float,float,float]]=None
    fit_type: FitType=FitType.SLIDING; needs_strength: bool=False
    needs_flexibility: bool=False; needs_water_resistance: bool=False
    wall_thickness_mm: float=2.0; corner_radius_mm: float=1.0; add_grip_texture: bool=False
    reference_object: str=""; similar_to: str=""; original_text: str=""
    extracted_numbers: List[float]=field(default_factory=list)
    confidence_score: float=0.0; top_candidates: List[Tuple[str,float]]=field(default_factory=list)
    clarification_needed: bool=False

    def to_dict(self):
        return {"name":self.name,"description":self.description,"category":self.category.value,
                "target_dimensions":[{"value":d.value,"unit":d.unit,"context":d.context,"mm":d.to_mm()} for d in self.target_dimensions],
                "max_dimensions_mm":self.max_dimensions,"fit_type":self.fit_type.value,
                "needs_strength":self.needs_strength,"wall_thickness_mm":self.wall_thickness_mm,
                "reference_object":self.reference_object,"similar_to":self.similar_to,
                "confidence_score":self.confidence_score,"top_candidates":self.top_candidates,
                "clarification_needed":self.clarification_needed}
    def to_json(self, indent=2): return json.dumps(self.to_dict(), indent=indent)
    def get_primary_dimension_mm(self):
        return self.target_dimensions[0].to_mm() if self.target_dimensions else None

@dataclass
class CategoryScore:
    category: ObjectCategory; raw_score: float; matched_keywords: List[str]
    penalized: bool; penalty_reason: str=""

class RequirementsParser:
    """Parses natural language requirements using context-aware scoring."""
    CONFIDENCE_THRESHOLD=5.0
    DIMENSION_PATTERNS=[
        r'(\d+\.?\d*)\s*(mm|cm|in|inch|inches?)\s*(diameter|wide|tall|long|thick|deep)?',
        r'(\d+\.?\d*)\s*(inches?|in|cm|mm)\s*(wide|tall|long|thick|deep|diameter)?',
        r'(diameter|width|height|length|thickness)\s*(?:of|:|\s)\s*(\d+\.?\d*)\s*(mm|cm|in)?',
        r'(\d+\.?\d*)\s*(oz|fl\s*oz|ml|liter|L)\s*(bottle|container|tube)?',
    ]
    CATEGORY_KEYWORDS={
        ObjectCategory.TUBE_SQUEEZER:[("tube squeezer",8,True),("toothpaste squeezer",8,True),("lotion squeezer",8,True),("squeezer",4,False),("squeeze",3,False),("toothpaste",3,False),("lotion",3,False),("cream",2,False),("paste",2,False),("dispenser",2,False),("roller",2,False),("wringer",2,False)],
        ObjectCategory.BRACKET:[("monitor stand",8,True),("shelf bracket",8,True),("wall mount",6,True),("corner brace",6,True),("l bracket",6,True),("l-shaped",5,True),("bracket",5,False),("mounting",3,False),("mount",2,False),("stand",1.5,False),("brace",3,False)],
        ObjectCategory.ENCLOSURE:[("electronics box",8,True),("project box",8,True),("raspberry pi",7,True),("arduino",6,False),("compartment",4,False),("cavity",4,False),("enclosure",6,False),("housing",5,False),("case",3,False),("container",3,False),("hollow",4,False),("lid",3,False),("storing",3,False),("inside",2,False),("shell",3,False),("cover",2,False)],
        ObjectCategory.BOX:[("rectangular prism",8,True),("calibration cube",8,True),("test cube",8,True),("solid block",6,True),("solid box",6,True),("no lid",5,True),("box",4,False)],
        ObjectCategory.CYLINDER:[("cylindrical rod",7,True),("round rod",6,True),("cylinder",5,False),("rod",3,False),("peg",3,False),("disc",3,False),("disk",3,False),("pin",3,False),("shaft",3,False),("round",2,False),("tube",2,False)],
        ObjectCategory.SPACER:[("spacer washer",7,True),("spacer ring",7,True),("standoff",6,False),("bushing",5,False),("grommet",5,False),("spacer",5,False),("washer",4,False),("pcb",2,False)],
        ObjectCategory.HOOK:[("wall hook",7,True),("coat hook",7,True),("hook",5,False),("hanger",4,False),("clip",1.5,False),("clamp",2,False),("grip",2,False),("grabber",2,False)],
        ObjectCategory.CUP_HOLDER:[("cup holder",10,True),("drink holder",8,True),("can holder",8,True),("bottle holder",7,True),("cup",4,False),("mug",4,False),("can",3,False),("beverage",3,False)],
        ObjectCategory.PHONE_STAND:[("phone stand",10,True),("phone holder",8,True),("mobile stand",8,True),("smartphone stand",9,True),("cell phone stand",9,True),("phone dock",7,True),("phone cradle",7,True),("phone",3,False),("smartphone",3,False)],
        ObjectCategory.KEYCHAIN:[("keychain",10,False),("key chain",10,True),("key ring",8,True),("key fob",8,True),("key tag",7,True),("key holder",7,True),("keyring",8,False),("key",2,False)],
        ObjectCategory.CABLE_CLIP:[("cable clip",10,True),("cable holder",8,True),("wire clip",9,True),("cord clip",9,True),("cable organizer",7,True),("cable management",7,True),("usb clip",8,True),("cable",3,False),("wire",3,False),("cord",3,False)],
    }
    EXCLUSION_RULES=[
        (["phone","smartphone","cell phone"],ObjectCategory.BRACKET,8),
        (["cable","wire","cord","usb"],ObjectCategory.HOOK,6),
        (["cup","mug","can","drink","beverage"],ObjectCategory.ENCLOSURE,5),
        (["key","keychain","keyring"],ObjectCategory.HOOK,5),
        (["puzzle","gear","vase"],ObjectCategory.BOX,10),
    ]
    STRENGTH_KEYWORDS=["strong","heavy duty","heavy-duty","robust","durable","sturdy","thick","reinforced","solid"]
    FLEX_KEYWORDS=["flexible","bendy","soft","elastic","springy","snap fit"]

    def __init__(self):
        self._compiled_patterns=[re.compile(p,re.IGNORECASE) for p in self.DIMENSION_PATTERNS]

    def parse(self, text: str) -> ModelRequirements:
        requirements=ModelRequirements(original_text=text)
        requirements.target_dimensions=self._extract_dimensions(text)
        requirements.extracted_numbers=self._extract_all_numbers(text)
        requirements.category, requirements.confidence_score, requirements.top_candidates, requirements.clarification_needed = self._classify_category(text)
        requirements.needs_strength=self._check_keywords(text,self.STRENGTH_KEYWORDS)
        requirements.needs_flexibility=self._check_keywords(text,self.FLEX_KEYWORDS)
        requirements.fit_type=self._determine_fit_type(text)
        requirements.reference_object=self._extract_reference(text)
        requirements.name=self._generate_name(requirements)
        requirements.description=self._generate_description(requirements)
        if requirements.needs_strength: requirements.wall_thickness_mm=3.0
        pd=requirements.get_primary_dimension_mm()
        if pd and pd>50: requirements.wall_thickness_mm=max(requirements.wall_thickness_mm,2.5)
        return requirements

    def _extract_dimensions(self, text: str) -> List[Dimension]:
        dimensions=[]; seen=set()
        for pattern in self._compiled_patterns:
            for m in pattern.finditer(text):
                g=m.groups()
                if len(g)>=2:
                    try:
                        if g[0].replace(".","").isdigit():
                            v=float(g[0]); u=g[1] if len(g)>1 else "mm"; c=g[2] if len(g)>2 and g[2] else ""
                        else:
                            c=g[0]; v=float(g[1]); u=g[2] if len(g)>2 and g[2] else "mm"
                        if v not in seen:
                            seen.add(v); dimensions.append(Dimension(value=v,unit=u,context=c or ""))
                    except (ValueError,IndexError): continue
        return dimensions

    def _extract_all_numbers(self, text: str) -> List[float]:
        nums=[]
        for m in re.finditer(r"\d+\.?\d*",text):
            try: nums.append(float(m.group()))
            except ValueError: continue
        return nums

    def _classify_category(self, text: str):
        tl=text.lower()
        scores={}
        matched_kws={}
        for cat,kws in self.CATEGORY_KEYWORDS.items():
            sc=0.0; mk=[]
            for kw,w,phrase in kws:
                if kw in tl:
                    if not phrase:
                        if not re.search(r"\b"+re.escape(kw)+r"\b",tl): continue
                    sc+=w*(2.0 if phrase else 1.0)
                    mk.append(kw)
            if sc>0:
                scores[cat]=sc
                matched_kws[cat]=mk
        # Apply exclusion penalties
        for words,blocked,penalty in self.EXCLUSION_RULES:
            if any(w in tl for w in words):
                if blocked in scores:
                    scores[blocked]=max(0,scores[blocked]-penalty)
        # Tie-breakers
        if ObjectCategory.ENCLOSURE in scores and ObjectCategory.BOX in scores and scores[ObjectCategory.ENCLOSURE]==scores[ObjectCategory.BOX]:
            scores[ObjectCategory.ENCLOSURE]+=0.1
        if ObjectCategory.SPACER in scores and ObjectCategory.BR