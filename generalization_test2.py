"""Three fresh generalization tests with unseen phrasing."""
from vibe_print.generator.requirements import RequirementsParser

p = RequirementsParser()

tests = [
    "something to prop my e-reader up on my desk",
    "a little dock so my phone doesn't just lie flat on the table",
    "I need to keep my charging cable from dangling off my nightstand",
]

print("=" * 70)
print("THREE FRESH GENERALIZATION TESTS")
print("=" * 70)

for desc in tests:
    req = p.parse(desc)
    status = "CLARIFY" if req.clarification_needed else req.category.value
    print(f"\nInput: {desc!r}")
    print(f"  category:             {status}")
    print(f"  confidence_score:     {req.confidence_score}")
    print(f"  clarification_needed: {req.clarification_needed}")
    print(f"  top_candidates:       {req.top_candidates}")
