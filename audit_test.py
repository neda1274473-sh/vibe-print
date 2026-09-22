"""Capability audit test script - runs 10 English requests through generate_from_description()."""

import json
from vibe_print.generator.cad_generator import ParametricGenerator
from vibe_print.generator.requirements import RequirementsParser

generator = ParametricGenerator()
parser = RequirementsParser()

test_requests = [
    "I need a small box to store screws, about 80mm wide",
    "Can you make a cup holder that clips onto a car vent",
    "I want a phone stand that holds my phone at an angle",
    "Make me a keychain with a hole for a ring",
    "I need a cable clip to hold a USB cable to my desk",
    "Design a simple gear with 20 teeth",
    "I want a vase, about 100mm tall",
    "Make a name tag holder with a pin clip",
    "I need a wall mount for my router",
    "Create a puzzle piece shape",
]

results = []

for i, request in enumerate(test_requests, 1):
    print(f"\n{'='*60}")
    print(f"TEST {i}: {request}")
    print(f"{'='*60}")
    
    # Parse requirements
    req = parser.parse(request)
    print(f"Detected category: {req.category.value}")
    print(f"Detected dimensions: {req.target_dimensions}")
    print(f"Extracted numbers: {req.extracted_numbers}")
    print(f"Generated name: {req.name}")
    print(f"Generated description: {req.description}")
    
    # Try generation
    try:
        result = generator.generate_from_description(request)
        print(f"Generation: SUCCESS")
        print(f"Model type: {result['model_type']}")
        print(f"Parameters: {result['parameters']}")
        print(f"Model path: {result['model_path']}")
        generation_success = True
    except Exception as e:
        print(f"Generation: FAILED - {e}")
        generation_success = False
        result = {"error": str(e)}
    
    results.append({
        "test_number": i,
        "input": request,
        "detected_category": req.category.value,
        "detected_dimensions": [
            {"value": d.value, "unit": d.unit, "context": d.context, "mm": d.to_mm()}
            for d in req.target_dimensions
        ],
        "extracted_numbers": req.extracted_numbers,
        "generated_name": req.name,
        "generated_description": req.description,
        "generation_success": generation_success,
        "model_type": result.get("model_type") if generation_success else None,
        "parameters": result.get("parameters") if generation_success else None,
        "model_path": result.get("model_path") if generation_success else None,
        "error": result.get("error") if not generation_success else None,
    })

# Save results
with open("audit_test_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
for r in results:
    status = "PASS" if r["generation_success"] else "FAIL"
    print(f"Test {r['test_number']}: {status} | category={r['detected_category']} | model_type={r['model_type'] or 'N/A'}")
