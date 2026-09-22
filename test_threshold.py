"""Determine optimal threshold by testing various values."""
from vibe_print.generator.semantic_classifier import SemanticClassifier

classifier = SemanticClassifier()

# Test cases: (sentence, expected_category or "clarify")
# "clarify" means we expect it to be below threshold
test_cases = [
    # Should PASS (correct category)
    ("phone stand for desk", "phone_stand"),
    ("smartphone stand", "phone_stand"),
    ("cell phone stand", "phone_stand"),
    ("phone dock", "phone_stand"),
    ("cable clip for desk", "cable_clip"),
    ("wire clip", "cable_clip"),
    ("cord clip", "cable_clip"),
    ("usb clip", "cable_clip"),
    ("cup holder for car", "cup_holder"),
    ("drink holder", "cup_holder"),
    ("bottle holder", "cup_holder"),
    ("keychain with my name", "keychain"),
    ("key chain", "keychain"),
    ("key fob", "keychain"),
    ("key tag", "keychain"),
    # Should CLARIFY (nonsense or unknown)
    ("gear", "clarify"),
    ("vase", "clarify"),
    ("puzzle piece", "clarify"),
    ("asdkjfh qwerty", "clarify"),
    ("xyz123 nonsense blabla", "clarify"),
    ("foo bar baz qux", "clarify"),
    # Part 3 test sentences
    ("something to prop my e-reader up on my desk", "phone_stand"),
    ("I want my tablet standing up while I watch videos", "phone_stand"),
    ("keep my charging cable from dangling off my nightstand", "cable_clip"),
    ("a way to stop my USB wire hanging off the table", "cable_clip"),
    ("holder so my drink doesn't tip over in the car", "cup_holder"),
    ("I need somewhere to put my coffee mug that won't spill", "cup_holder"),
    ("a little tag with a hole so I can put my house key on a ring", "keychain"),
    ("flat token with a loop for my keys", "keychain"),
    ("a wedge to lean my iPad against while I cook", "phone_stand"),
    ("something round with a hole in the middle to go around a bolt", "spacer"),
    ("an L-shaped piece to hold up a shelf", "bracket"),
    ("a container with a lid to keep my Arduino dust-free", "enclosure"),
]

print("Threshold analysis:")
print("=" * 80)
for threshold in [0.30, 0.35, 0.40, 0.42, 0.45, 0.50, 0.55]:
    correct = 0
    total = len(test_cases)
    errors = []
    for sentence, expected in test_cases:
        cat, score, top3, clarify = classifier.classify(sentence)
        if expected == "clarify":
            if clarify:
                correct += 1
            else:
                errors.append(f"  {sentence!r}: got {cat.value} ({score:.3f}), expected clarify")
        else:
            if cat.value == expected and not clarify:
                correct += 1
            elif clarify:
                errors.append(f"  {sentence!r}: got CLARIFY ({score:.3f}), expected {expected}")
            else:
                errors.append(f"  {sentence!r}: got {cat.value} ({score:.3f}), expected {expected}")
    print(f"\nThreshold {threshold}: {correct}/{total} correct")
    for e in errors:
        print(e)
