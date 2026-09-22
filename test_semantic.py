"""Test script for semantic classifier — Part 3 verification sentences."""
import time
from vibe_print.generator.semantic_classifier import SemanticClassifier

TEST_SENTENCES = [
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

# Also test some existing training-like sentences to see score distribution
EXISTING_SENTENCES = [
    "phone stand for desk",
    "smartphone stand",
    "cell phone stand",
    "phone dock",
    "cable clip for desk",
    "wire clip",
    "cord clip",
    "usb clip",
    "cup holder for car",
    "drink holder",
    "can holder for desk",
    "bottle holder",
    "keychain with my name",
    "key chain",
    "key fob",
    "key tag",
    "gear",
    "vase",
    "puzzle piece",
    "name tag holder",
]

print("Loading classifier...")
start = time.time()
classifier = SemanticClassifier()
print(f"Loaded in {time.time() - start:.2f}s\n")

print("=" * 70)
print("PART 3 — TEST SENTENCES")
print("=" * 70)
for sentence, expected in TEST_SENTENCES:
    cat, score, top3, clarify = classifier.classify(sentence)
    status = "OK" if cat.value == expected else ("CLARIFY" if clarify else "WRONG")
    print(f"\nInput:    {sentence}")
    print(f"Expected: {expected}")
    print(f"Got:      {cat.value} (score={score:.3f}, clarify={clarify}) [{status}]")
    print(f"Top 3:    {top3}")

print("\n" + "=" * 70)
print("SCORE DISTRIBUTION — EXISTING / TRAINING-LIKE SENTENCES")
print("=" * 70)
for sentence in EXISTING_SENTENCES:
    cat, score, top3, clarify = classifier.classify(sentence)
    print(f"{score:.3f}  {cat.value:15s}  clarify={clarify}  |  {sentence}")

print("\n" + "=" * 70)
print("NONSENSE INPUT")
print("=" * 70)
for nonsense in ["asdkjfh qwerty", "xyz123 nonsense blabla", "foo bar baz qux"]:
    cat, score, top3, clarify = classifier.classify(nonsense)
    print(f"{score:.3f}  {cat.value:15s}  clarify={clarify}  |  {nonsense}")

print("\n" + "=" * 70)
print("LATENCY TEST (after warm-up)")
print("=" * 70)
# Warm-up already done
latencies = []
for _ in range(20):
    t0 = time.time()
    classifier.classify("a phone stand for my desk")
    latencies.append((time.time() - t0) * 1000)
print(f"Mean latency: {sum(latencies)/len(latencies):.2f} ms")
print(f"Min latency:  {min(latencies):.2f} ms")
print(f"Max latency:  {max(latencies):.2f} ms")
