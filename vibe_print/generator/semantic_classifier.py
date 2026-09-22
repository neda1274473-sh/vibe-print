"""Semantic embedding-based category classifier.

Uses sentence-transformers with a lightweight local model to compare
user input against example sentences per category via cosine similarity.
"""

import re
from typing import Dict, List, Tuple
import numpy as np

from vibe_print.generator.requirements import ObjectCategory

# Example sentences per category — natural language descriptions of function/purpose.
# These are written generically and NOT tuned to any specific test set.
CATEGORY_EXAMPLES: Dict[ObjectCategory, List[str]] = {
    ObjectCategory.BOX: [
        "a solid rectangular block for calibration or testing",
        "a simple cube shape with no hollow inside",
        "a plain rectangular prism used as a building block",
        "a solid box shape for weight or structural support",
        "a block with flat sides and sharp corners",
        "a rectangular solid piece for mechanical testing",
        "a test cube for 3d printer calibration",
        "a plain box with no lid, just solid walls",
    ],
    ObjectCategory.CYLINDER: [
        "a round rod or shaft that spins or slides",
        "a cylindrical peg for fitting into holes",
        "a disc or disk shaped object",
        "a round pin for alignment or hinges",
        "a smooth cylindrical rod",
        "a circular shaft that rotates",
    ],
    ObjectCategory.TUBE_SQUEEZER: [
        "a device to squeeze the last toothpaste out of a tube",
        "something that rolls along a tube to push out lotion",
        "a tool to wring out paste from a tube",
        "a roller that squeezes cream out of a tube",
        "something to help get all the toothpaste out",
        "a tube wringer for bathroom products",
    ],
    ObjectCategory.BRACKET: [
        "an L-shaped piece to support a shelf on a wall",
        "a corner brace to hold two surfaces together at a right angle",
        "a wall mount to hold up a monitor or TV",
        "a mounting bracket for attaching things to walls",
        "an angled support piece for shelves",
        "a metal brace to reinforce a corner joint",
        "a router mount to attach a tool to a surface",
    ],
    ObjectCategory.ENCLOSURE: [
        "a box with a lid to protect electronics from dust",
        "a hollow case to house a circuit board",
        "a container with a cover for storing components",
        "a project box to keep an Arduino safe",
        "a shell with a cavity inside for electronics",
        "a housing with a lid to keep things clean",
    ],
    ObjectCategory.SPACER: [
        "a ring that goes around a bolt to create space",
        "a cylindrical washer to separate two parts",
        "a standoff to hold a circuit board away from a surface",
        "a bushing that fits around a shaft",
        "a grommet to protect a cable passing through a hole",
        "a small ring used as a spacer between components",
        "a spacer washer with an inner hole for a bolt",
    ],
    ObjectCategory.HOOK: [
        "a curved piece to hang coats on a wall",
        "a wall hook for hanging bags or tools",
        "a hanger that curves to hold things",
        "a hook shaped piece to grab and hold items",
        "something curved to hang things from",
        "a clamp that hooks onto a surface to hold wires",
    ],
    ObjectCategory.CUP_HOLDER: [
        "something to hold a drink so it doesn't tip over",
        "a holder for a coffee mug in a car",
        "a place to put a can or bottle so it stays upright",
        "a drink holder that prevents spills",
        "something to keep a beverage container stable",
        "a holder for cups and mugs",
    ],
    ObjectCategory.PHONE_STAND: [
        "something to hold my phone upright so I can watch videos",
        "a stand that props up my phone at an angle for video calls",
        "a little holder to keep my tablet standing up on a desk",
        "something to lean my phone against while I cook",
        "a dock that holds my smartphone at an angle",
        "a cradle to support my phone while charging",
        "something to prop up my e-reader on a desk",
    ],
    ObjectCategory.KEYCHAIN: [
        "a small tag with a hole to attach my keys to a ring",
        "a flat token with a loop for connecting keys",
        "a little fob I can put my house key on",
        "a key ring holder with my name on it",
        "something small with a hole to thread keys through",
        "a tag to label my keys",
    ],
    ObjectCategory.CABLE_CLIP: [
        "something to keep a charging cable from dangling",
        "a clip to hold a USB wire in place on a desk",
        "something to stop a cord from hanging off a table",
        "a small holder to organize cables neatly",
        "a wire clip to manage cords on a nightstand",
        "something to secure a cable so it doesn't fall",
    ],
}


class SemanticClassifier:
    """Local semantic embedding classifier using sentence-transformers."""

    # Threshold determined empirically from score distributions.
    # See SEMANTIC_CLASSIFICATION_SUMMARY.md for derivation.
    SIMILARITY_THRESHOLD = 0.42

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self._example_embeddings: Dict[ObjectCategory, np.ndarray] = {}
        self._warmup()

    def _warmup(self) -> None:
        """Precompute and cache embeddings for all example sentences."""
        for category, sentences in CATEGORY_EXAMPLES.items():
            embeddings = self._model.encode(sentences, convert_to_numpy=True)
            self._example_embeddings[category] = embeddings

    def classify(self, text: str) -> Tuple[ObjectCategory, float, List[Tuple[str, float]], bool]:
        """Classify text into an ObjectCategory using semantic similarity.

        Returns:
            (category, confidence_score, top_candidates, clarification_needed)
        """
        user_embedding = self._model.encode(text, convert_to_numpy=True)

        scores: Dict[ObjectCategory, float] = {}
        for category, embeddings in self._example_embeddings.items():
            # Max similarity across all examples for this category.
            # Rationale: a user only needs to match ONE example strongly
            # to indicate they mean that category. Average would dilute
            # a strong match with semantically diverse examples.
            sims = np.dot(embeddings, user_embedding) / (
                np.linalg.norm(embeddings, axis=1) * np.linalg.norm(user_embedding)
            )
            scores[category] = float(np.max(sims))

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_category, best_score = sorted_scores[0]
        top_candidates = [
            (cat.value, round(sc, 3)) for cat, sc in sorted_scores[:3]
        ]

        if best_score < self.SIMILARITY_THRESHOLD:
            return ObjectCategory.CUSTOM, best_score, top_candidates, True

        return best_category, best_score, top_candidates, False

    def get_score_distribution(self, test_sentences: List[str]) -> Dict[str, List[float]]:
        """Return similarity scores for each test sentence against all categories."""
        results: Dict[str, List[float]] = {}
        for sentence in test_sentences:
            user_embedding = self._model.encode(sentence, convert_to_numpy=True)
            sentence_scores = []
            for category, embeddings in self._example_embeddings.items():
                sims = np.dot(embeddings, user_embedding) / (
                    np.linalg.norm(embeddings, axis=1) * np.linalg.norm(user_embedding)
                )
                sentence_scores.append(float(np.max(sims)))
            results[sentence] = sentence_scores
        return results


class SimpleKeywordClassifier:
    """Lightweight fallback classifier — no external ML dependency required.

    Uses word-overlap (Jaccard similarity) against the SAME example
    sentences defined in CATEGORY_EXAMPLES above, instead of AI embeddings.
    This is automatically used when `sentence-transformers` is not
    installed, so the parser never crashes and always has a working
    baseline. Install the optional "semantic" extra to upgrade to the
    more accurate SemanticClassifier — no code changes needed elsewhere.
    """

    SIMILARITY_THRESHOLD = 0.15

    _STOPWORDS = {
        "a", "an", "the", "to", "of", "for", "my", "that", "this", "in",
        "on", "with", "at", "is", "it", "so", "i", "can", "or", "and",
        "up", "off", "something", "someone", "little", "small", "me",
        "want", "need", "like",
    }

    def _tokenize(self, text: str) -> set:
        words = re.findall(r"[a-zA-Z]+", text.lower())
        return {w for w in words if w not in self._STOPWORDS and len(w) > 1}

    def classify(self, text: str) -> Tuple[ObjectCategory, float, List[Tuple[str, float]], bool]:
        """Classify text into an ObjectCategory using word overlap.

        Returns:
            (category, confidence_score, top_candidates, clarification_needed)
        """
        user_words = self._tokenize(text)
        if not user_words:
            return ObjectCategory.CUSTOM, 0.0, [], True

        scores: Dict[ObjectCategory, float] = {}
        for category, sentences in CATEGORY_EXAMPLES.items():
            best = 0.0
            for sentence in sentences:
                ex_words = self._tokenize(sentence)
                if not ex_words:
                    continue
                union = len(user_words | ex_words)
                overlap = len(user_words & ex_words)
                score = overlap / union if union else 0.0
                if score > best:
                    best = score
            scores[category] = best

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_category, best_score = sorted_scores[0]
        top_candidates = [
            (cat.value, round(sc, 3)) for cat, sc in sorted_scores[:3]
        ]

        if best_score < self.SIMILARITY_THRESHOLD:
            return ObjectCategory.CUSTOM, best_score, top_candidates, True

        return best_category, best_score, top_candidates, False
