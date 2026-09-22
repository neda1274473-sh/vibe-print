"""10-case audit re-test script for the Understanding Upgrade."""
from vibe_print.generator.requirements import RequirementsParser

p = RequirementsParser()

audit_cases = [
    "cup holder for car",
    "phone stand for desk",
    "keychain with my name",
    "cable clip for desk",
    "gear",
    "vase",
    "name tag holder",
    "puzzle piece",
    "router mount",
]

print("=" * 80)
print("10-CASE AUDIT RE-TEST (after upgrade)")
print("=" * 80)
for case in audit_cases:
    r = p.parse(case)
    status = "CLARIFY" if r.clarification_needed else r.category.value
    print(
        f"{case!r:35} -> {status:15} "
        f"(score={r.confidence_score:5.1f}, clarify={r.clarification_needed})"
    )
    if r.top_candidates:
        print(f"  top candidates: {r.top_candidates}")

print()
print("Summary:")
correct = sum(
    1
    for c in audit_cases
    if not p.parse(c).clarification_needed and p.parse(c).category.value != "custom"
)
clarify = sum(1 for c in audit_cases if p.parse(c).clarification_needed)
print(f"  Correctly routed:      {correct}/{len(audit_cases)}")
print(f"  Honest clarification:  {clarify}/{len(audit_cases)}")
print(
    f"  Accuracy (correct + honest clarify): "
    f"{(correct + clarify)}/{len(audit_cases)} = {((correct + clarify) / len(audit_cases) * 100):.0f}%"
)
