import sys, traceback
sys.path.insert(0, ".")
try:
    from vibe_print.generator.semantic_classifier import SimpleKeywordClassifier
    print("SimpleKeywordClassifier OK:", SimpleKeywordClassifier)
except Exception:
    traceback.print_exc()