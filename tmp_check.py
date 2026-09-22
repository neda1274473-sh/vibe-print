from vibe_print.generator.semantic_classifier import SemanticClassifier

cls = SemanticClassifier()

queries = [
    'test cube 20mm',
    'plain box with no lid',
    'spacer washer 8mm inner hole',
    'clamp for holding wires',
    'can holder for desk',
    'gear',
    'vase',
    'name tag holder',
    'puzzle piece',
    'router mount',
    'boxing glove holder',
    'box with lid and hollow inside',
    'I want a little stand to prop up my tablet while I watch videos in bed',
]

for q in queries:
    cat, score, _, clar = cls.classify(q)
    print(f"{q}: {cat.value} (score={score:.3f}, clarify={clar})")
