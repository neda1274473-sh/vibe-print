"""Fresh generalization test with unseen phrasing."""
from vibe_print.generator.requirements import RequirementsParser
from vibe_print.generator.cad_generator import ParametricGenerator

p = RequirementsParser()
g = ParametricGenerator()

description = "I want a little stand to prop up my tablet while I watch videos in bed"

print("=" * 70)
print("FRESH GENERALIZATION TEST")
print("=" * 70)
print(f"Input: {description!r}")
print()

# Parse
req = p.parse(description)
print("--- RequirementsParser.parse() ---")
print(f"  category:             {req.category.value}")
print(f"  confidence_score:     {req.confidence_score}")
print(f"  clarification_needed: {req.clarification_needed}")
print(f"  top_candidates:       {req.top_candidates}")
print()

# Generate
result = g.generate_from_description(description)
print("--- ParametricGenerator.generate_from_description() ---")
print(f"  model_type:           {result['model_type']}")
print(f"  parameters:           {result['parameters']}")
print(f"  model_path:           {result['model_path']}")
print(f"  requirements.category: {result['requirements']['category']}")
print(f"  requirements.clarification_needed: {result['requirements']['clarification_needed']}")
print(f"  requirements.confidence_score: {result['requirements']['confidence_score']}")
print(f"  requirements.top_candidates: {result['requirements']['top_candidates']}")
print()

# Honest assessment
print("--- HONEST ASSESSMENT ---")
if req.clarification_needed:
    print("Result: CLARIFICATION (honest uncertainty)")
elif result["model_type"] == "phone_stand":
    print("Result: CORRECT-ish (routed to phone_stand, closest match)")
elif result["model_type"] == "bracket":
    print("Result: MISROUTE (tablet stand went to bracket — generalization failure)")
else:
    print(f"Result: {result['model_type']}")
