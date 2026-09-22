"""
Permanent routing accuracy tests for RequirementsParser.

These tests prevent silent regressions in natural-language-to-category routing.
Every supported generator category must have at least 5 test cases,
including synonyms and deliberately ambiguous phrases.
"""

import importlib.util

import pytest
from vibe_print.generator.requirements import RequirementsParser, ObjectCategory
from vibe_print.generator.semantic_classifier import SemanticClassifier

# These tests validate the *semantic* (embedding-based) classifier's ability
# to generalize across paraphrases. That accuracy is only available when the
# optional `sentence-transformers` dependency is installed. Without it, the
# parser automatically falls back to a simpler word-overlap classifier that
# is not expected to pass this specific accuracy bar — so we skip cleanly
# instead of reporting false failures.
pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("sentence_transformers") is None,
    reason="Requires optional AI dependency: pip install -e .[semantic]",
)


class TestRoutingAccuracy:
    """Comprehensive routing tests — 46 cases covering all 7 categories + edge cases."""

    @pytest.fixture
    def parser(self):
        return RequirementsParser()

    # ------------------------------------------------------------------
    # BOX (6 cases)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("description", [
        "a simple rectangular box 50mm wide",
        "solid block for calibration",
        "test cube 20mm",
        "rectangular prism 30x40x50",
        "plain box with no lid",
        "solid box for weight",
    ])
    def test_box_routing(self, parser, description):
        req = parser.parse(description)
        assert req.category == ObjectCategory.BOX, (
            f"'{description}' should route to BOX, got {req.category.value}"
        )

    # ------------------------------------------------------------------
    # CYLINDER (6 cases)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("description", [
        "a round cylinder 40mm diameter",
        "cylindrical rod for my project",
        "peg 8mm diameter",
        "disc 25mm wide",
        "pin for hinge",
        "round shaft 10mm",
    ])
    def test_cylinder_routing(self, parser, description):
        req = parser.parse(description)
        assert req.category == ObjectCategory.CYLINDER, (
            f"'{description}' should route to CYLINDER, got {req.category.value}"
        )

    # ------------------------------------------------------------------
    # TUBE_SQUEEZER (6 cases)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("description", [
        "tube squeezer for 65mm lotion bottle",
        "something to hold my toothpaste tube",
        "toothpaste squeezer",
        "lotion squeezer",
        "cream dispenser roller",
        "paste wringer",
    ])
    def test_tube_squeezer_routing(self, parser, description):
        req = parser.parse(description)
        assert req.category == ObjectCategory.TUBE_SQUEEZER, (
            f"'{description}' should route to TUBE_SQUEEZER, got {req.category.value}"
        )

    # ------------------------------------------------------------------
    # BRACKET (6 cases)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("description", [
        "L-shaped bracket for shelf mounting",
        "corner brace for my desk",
        "wall mount for tv",
        "shelf bracket 100mm",
        "L bracket for cabinet",
        "mounting bracket for sensor",
    ])
    def test_bracket_routing(self, parser, description):
        req = parser.parse(description)
        assert req.category == ObjectCategory.BRACKET, (
            f"'{description}' should route to BRACKET, got {req.category.value}"
        )

    # ------------------------------------------------------------------
    # ENCLOSURE (6 cases)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("description", [
        "electronics project box 80x50x30",
        "hollow case for raspberry pi",
        "container with lid for storing screws",
        "arduino housing with cavity",
        "project box with compartment",
        "shell cover for electronics",
    ])
    def test_enclosure_routing(self, parser, description):
        req = parser.parse(description)
        assert req.category == ObjectCategory.ENCLOSURE, (
            f"'{description}' should route to ENCLOSURE, got {req.category.value}"
        )

    # ------------------------------------------------------------------
    # SPACER (6 cases)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("description", [
        "spacer washer 8mm inner hole",
        "cylindrical standoff for my board",
        "bushing for 10mm shaft",
        "grommet for cable",
        "spacer ring 12mm",
        "washer for bolt",
    ])
    def test_spacer_routing(self, parser, description):
        req = parser.parse(description)
        assert req.category == ObjectCategory.SPACER, (
            f"'{description}' should route to SPACER, got {req.category.value}"
        )

    # ------------------------------------------------------------------
    # HOOK (6 cases)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("description", [
        "wall hook for hanging coats",
        "curved hanger for my garage wall",
        "coat hook for door",
        "clip for bag",
        "clamp for holding wires",
        "grip grabber for tools",
    ])
    def test_hook_routing(self, parser, description):
        req = parser.parse(description)
        assert req.category == ObjectCategory.HOOK, (
            f"'{description}' should route to HOOK, got {req.category.value}"
        )

    # ------------------------------------------------------------------
    # Ambiguous / edge cases (4 cases)
    # ------------------------------------------------------------------
    def test_box_vs_enclosure_lid_wins_enclosure(self, parser):
        """Both box and enclosure signals present -> enclosure wins."""
        req = parser.parse("box with lid and hollow inside")
        assert req.category == ObjectCategory.ENCLOSURE

    def test_box_vs_enclosure_solid_wins_box(self, parser):
        """Solid signal without enclosure signals -> box."""
        req = parser.parse("solid block 20mm cube")
        assert req.category == ObjectCategory.BOX

    def test_standoff_vs_bracket_standoff_wins_spacer(self, parser):
        """'standoff' is a specific spacer term that must beat generic 'mounting'."""
        req = parser.parse("standoff for pcb mounting")
        assert req.category == ObjectCategory.SPACER

    def test_monitor_stand_routes_to_bracket(self, parser):
        """'monitor stand' is a specific bracket phrase."""
        req = parser.parse("stand for monitor")
        assert req.category == ObjectCategory.BRACKET

    # ------------------------------------------------------------------
    # NEW CATEGORIES — Part 2 expansion (4 cases each)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("description", [
        "cup holder for car",
        "drink holder",
        "can holder for desk",
        "bottle holder",
    ])
    def test_cup_holder_routing(self, parser, description):
        req = parser.parse(description)
        assert req.category == ObjectCategory.CUP_HOLDER, (
            f"'{description}' should route to CUP_HOLDER, got {req.category.value}"
        )

    @pytest.mark.parametrize("description", [
        "phone stand for desk",
        "smartphone stand",
        "cell phone stand",
        "phone dock",
    ])
    def test_phone_stand_routing(self, parser, description):
        req = parser.parse(description)
        assert req.category == ObjectCategory.PHONE_STAND, (
            f"'{description}' should route to PHONE_STAND, got {req.category.value}"
        )

    @pytest.mark.parametrize("description", [
        "keychain with my name",
        "key chain",
        "key fob",
        "key tag",
    ])
    def test_keychain_routing(self, parser, description):
        req = parser.parse(description)
        assert req.category == ObjectCategory.KEYCHAIN, (
            f"'{description}' should route to KEYCHAIN, got {req.category.value}"
        )

    @pytest.mark.parametrize("description", [
        "cable clip for desk",
        "wire clip",
        "cord clip",
        "usb clip",
    ])
    def test_cable_clip_routing(self, parser, description):
        req = parser.parse(description)
        assert req.category == ObjectCategory.CABLE_CLIP, (
            f"'{description}' should route to CABLE_CLIP, got {req.category.value}"
        )

    # ------------------------------------------------------------------
    # AUDIT FIXES — 9 cases that previously failed silently (Part 1)
    # ------------------------------------------------------------------
    def test_phone_stand_not_routed_to_bracket(self, parser):
        """Audit bug: 'phone stand' was caught by 'stand' -> bracket."""
        req = parser.parse("phone stand")
        assert req.category == ObjectCategory.PHONE_STAND
        assert not req.clarification_needed

    def test_cable_clip_not_routed_to_hook(self, parser):
        """Audit bug: 'cable clip' was caught by 'clip' -> hook."""
        req = parser.parse("cable clip")
        assert req.category == ObjectCategory.CABLE_CLIP
        assert not req.clarification_needed

    def test_gear_returns_clarification(self, parser):
        """Audit bug: 'gear' silently fell to custom -> generic box."""
        req = parser.parse("gear")
        assert req.category == ObjectCategory.CUSTOM
        assert req.clarification_needed
        assert req.confidence_score < SemanticClassifier.SIMILARITY_THRESHOLD

    def test_vase_returns_clarification(self, parser):
        """Audit bug: 'vase' silently fell to custom -> generic box."""
        req = parser.parse("vase")
        assert req.category == ObjectCategory.CUSTOM
        assert req.clarification_needed
        assert req.confidence_score == 0.0

    def test_name_tag_holder_returns_clarification(self, parser):
        """Audit bug: 'name tag holder' silently fell to custom -> generic box."""
        req = parser.parse("name tag holder")
        assert req.category == ObjectCategory.CUSTOM
        assert req.clarification_needed

    def test_puzzle_piece_returns_clarification(self, parser):
        """Audit bug: 'puzzle piece' silently fell to custom -> generic box."""
        req = parser.parse("puzzle piece")
        assert req.category == ObjectCategory.CUSTOM
        assert req.clarification_needed
        assert req.confidence_score < SemanticClassifier.SIMILARITY_THRESHOLD

    def test_router_mount_routes_to_bracket(self, parser):
        """'router mount' is a legitimate bracket request."""
        req = parser.parse("router mount")
        assert req.category == ObjectCategory.BRACKET
        assert not req.clarification_needed

    def test_cup_holder_not_routed_to_enclosure(self, parser):
        """Audit bug: 'cup holder' was caught by 'holder' -> enclosure."""
        req = parser.parse("cup holder")
        assert req.category == ObjectCategory.CUP_HOLDER
        assert not req.clarification_needed

    def test_keychain_not_routed_to_hook(self, parser):
        """Audit bug: 'keychain' was caught by 'chain' or generic matching."""
        req = parser.parse("keychain")
        assert req.category == ObjectCategory.KEYCHAIN
        assert not req.clarification_needed


class TestCollisionPrevention:
    """Tests that prove the longest-match-first / word-boundary approach works."""

    @pytest.fixture
    def parser(self):
        return RequirementsParser()

    def test_standoff_not_caught_by_stand(self, parser):
        """Phase 2.75 bug: 'standoff' was caught by 'stand' -> bracket."""
        req = parser.parse("standoff for pcb")
        assert req.category == ObjectCategory.SPACER

    def test_tube_squeezer_not_caught_by_squeezer_alone(self, parser):
        """'tube squeezer' phrase should win over generic 'squeezer'."""
        req = parser.parse("tube squeezer")
        assert req.category == ObjectCategory.TUBE_SQUEEZER

    def test_box_not_caught_by_boxing(self, parser):
        """Word-boundary guard: 'boxing' should not match 'box'."""
        req = parser.parse("boxing glove holder")
        assert req.category != ObjectCategory.BOX

    def test_no_lid_scores_higher_than_lid(self, parser):
        """'no lid' (6 chars) in BOX should score higher than 'lid' (3) in ENCLOSURE."""
        req = parser.parse("plain box with no lid")
        assert req.category == ObjectCategory.BOX

    def test_tablet_stand_generalization(self, parser):
        """Unseen phrasing 'prop up my tablet' routes to phone_stand, not bracket."""
        req = parser.parse(
            "I want a little stand to prop up my tablet while I watch videos in bed"
        )
        assert req.category == ObjectCategory.PHONE_STAND
        assert not req.clarification_needed
        assert req.confidence_score >= 0.5
        bracket_score = next(
            (sc for cat, sc in req.top_candidates if cat == "bracket"), 0
        )
        assert bracket_score < req.confidence_score
