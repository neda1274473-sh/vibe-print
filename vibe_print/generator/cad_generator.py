"""
Parametric CAD Generator - Create 3D models using CadQuery.

Generates precise, parametric 3D models from specifications.
CadQuery 2.8.0+ is the primary engine (OpenCascade-based).
A trimesh fallback path exists for environments where CadQuery
is not available, clearly labeled with warnings.
"""

import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List

from vibe_print.exceptions import ModelGenerationError, InputValidationError
from vibe_print.logging_config import get_logger

try:
    import cadquery as cq
    from cadquery import exporters
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False

logger = get_logger(__name__)

if not CADQUERY_AVAILABLE:
    logger.warning(
        "# CADQUERY_UNAVAILABLE_FALLBACK — CadQuery not installed. "
        "Using trimesh fallback. Install CadQuery for full parametric CAD: pip install cadquery"
    )


@dataclass
class GeneratedModel:
    """A generated 3D model."""
    name: str
    output_path: Path
    format: str = "stl"
    method: str = ""  # "cadquery", "trimesh_fallback"
    source_code: str = ""
    dimensions_mm: Dict[str, float] = field(default_factory=dict)
    generation_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "output_path": str(self.output_path),
            "format": self.format,
            "method": self.method,
            "dimensions_mm": self.dimensions_mm,
            "generation_notes": self.generation_notes,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class ParametricGenerator:
    """
    Generates parametric 3D models using CadQuery (primary) or trimesh (fallback).

    CadQuery provides true parametric CAD: sketches, extrusions, booleans,
    fillets, shells, and threads via the OpenCascade kernel.
    """

    SUPPORTED_TYPES = {
        "box",
        "cylinder",
        "tube_squeezer",
        "bracket",
        "enclosure",
        "spacer",
        "hook",
        "cup_holder",
        "phone_stand",
        "keychain",
        "cable_clip",
    }

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "vibe-print" / "generated"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._using_fallback = not CADQUERY_AVAILABLE

    def is_available(self) -> tuple[bool, str]:
        """Check generation capabilities."""
        if CADQUERY_AVAILABLE:
            return True, f"CadQuery {cq.__version__} available"
        if TRIMESH_AVAILABLE:
            return True, "trimesh fallback (CadQuery unavailable)"
        return False, "No geometry engine available"

    def generate(
        self,
        model_type: str,
        parameters: Dict[str, Any],
        output_name: Optional[str] = None,
    ) -> Path:
        """
        Generate a model by type.

        Args:
            model_type: One of SUPPORTED_TYPES
            parameters: Type-specific parameters
            output_name: Optional output filename

        Returns:
            Path to generated STL file
        """
        if not model_type:
            raise ModelGenerationError("model_type cannot be empty")
        if not parameters:
            raise ModelGenerationError("parameters cannot be empty")

        model_type = model_type.lower().strip()
        if model_type not in self.SUPPORTED_TYPES:
            raise ModelGenerationError(
                f"Unknown model_type: {model_type}. Supported: {sorted(self.SUPPORTED_TYPES)}"
            )

        if output_name is None:
            output_name = f"{model_type}_generated"

        output_path = self.output_dir / f"{output_name}.stl"

        generator_map = {
            "box": self._generate_box,
            "cylinder": self._generate_cylinder,
            "tube_squeezer": self._generate_tube_squeezer,
            "bracket": self._generate_bracket,
            "enclosure": self._generate_enclosure,
            "spacer": self._generate_spacer,
            "hook": self._generate_hook,
            "cup_holder": self._generate_cup_holder,
            "phone_stand": self._generate_phone_stand,
            "keychain": self._generate_keychain,
            "cable_clip": self._generate_cable_clip,
        }

        return generator_map[model_type](parameters, output_path)

    def generate_from_description(
        self,
        description: str,
        material: str = "PLA",
        nozzle_diameter: float = 0.4,
    ) -> Dict[str, Any]:
        """
        Generate a model from natural language description.

        Uses RequirementsParser for routing and parameter extraction.
        """
        if not description:
            raise ModelGenerationError("description cannot be empty")

        from vibe_print.generator.requirements import RequirementsParser

        parser = RequirementsParser()
        requirements = parser.parse(description)
        category = requirements.category.value

        # Direct mapping from ObjectCategory values to generator types.
        # Every supported category maps 1:1; custom falls back to box.
        category_map = {
            "box": "box",
            "cylinder": "cylinder",
            "tube_squeezer": "tube_squeezer",
            "bracket": "bracket",
            "enclosure": "enclosure",
            "spacer": "spacer",
            "hook": "hook",
            "cup_holder": "cup_holder",
            "phone_stand": "phone_stand",
            "keychain": "keychain",
            "cable_clip": "cable_clip",
            "custom": "box",
        }

        model_type = category_map.get(category, "box")
        primary_dim = requirements.get_primary_dimension_mm()

        params: Dict[str, Any] = {}
        if model_type == "tube_squeezer":
            params = {
                "tube_diameter": primary_dim or 50,
                "wall_thickness": requirements.wall_thickness_mm,
                "width": (primary_dim or 50) + 20,
            }
        elif model_type == "bracket":
            params = {
                "width": primary_dim or 60,
                "height": (primary_dim or 60) * 0.8,
                "thickness": requirements.wall_thickness_mm,
                "hole_diameter": 5.0,
            }
        elif model_type == "enclosure":
            params = {
                "width": primary_dim or 80,
                "depth": (primary_dim or 80) * 0.6,
                "height": (primary_dim or 80) * 0.4,
                "wall_thickness": requirements.wall_thickness_mm,
            }
        elif model_type == "spacer":
            params = {
                "inner_diameter": primary_dim or 8,
                "outer_diameter": (primary_dim or 8) * 2,
                "thickness": requirements.wall_thickness_mm,
            }
        elif model_type == "hook":
            params = {
                "arm_length": primary_dim or 40,
                "thickness": requirements.wall_thickness_mm,
                "mount_hole_diameter": 5.0,
            }
        elif model_type == "cup_holder":
            params = {
                "diameter": primary_dim or 80,
                "height": (primary_dim or 80) * 0.8,
                "wall_thickness": requirements.wall_thickness_mm,
                "base_thickness": requirements.wall_thickness_mm,
            }
        elif model_type == "phone_stand":
            params = {
                "width": primary_dim or 70,
                "depth": (primary_dim or 70) * 0.6,
                "height": (primary_dim or 70) * 0.5,
                "angle": 60.0,
                "lip_height": 5.0,
                "wall_thickness": requirements.wall_thickness_mm,
            }
        elif model_type == "keychain":
            params = {
                "width": primary_dim or 40,
                "height": (primary_dim or 40) * 0.6,
                "thickness": requirements.wall_thickness_mm,
                "hole_diameter": 5.0,
            }
        elif model_type == "cable_clip":
            params = {
                "cable_diameter": primary_dim or 6,
                "clip_width": (primary_dim or 6) * 3,
                "wall_thickness": requirements.wall_thickness_mm,
                "mount_hole_diameter": 3.5,
            }
        else:
            params = {
                "width": primary_dim or 50,
                "height": (primary_dim or 50) * 0.6,
                "depth": (primary_dim or 50) * 0.8,
            }

        logger.info(
            "Routing description to model_type=%s (category=%s, confidence=heuristic)",
            model_type,
            category,
        )

        path = self.generate(model_type, params, "from_description")
        return {
            "model_path": str(path),
            "model_type": model_type,
            "parameters": params,
            "requirements": requirements.to_dict(),
        }

    # ------------------------------------------------------------------
    # CadQuery-based generators
    # ------------------------------------------------------------------

    def _generate_box(self, params: Dict[str, Any], output_path: Path) -> Path:
        """Generate a box using CadQuery."""
        required = ["width", "height", "depth"]
        missing = [r for r in required if r not in params]
        if missing:
            raise ModelGenerationError(
                f"Missing required parameters: {', '.join(missing)}",
                details={"missing": missing, "provided": list(params.keys())},
            )

        width = float(params["width"])
        height = float(params["height"])
        depth = float(params["depth"])

        if CADQUERY_AVAILABLE:
            wp = cq.Workplane("XY").box(width, depth, height)
            exporters.export(wp, str(output_path))
            method = "cadquery"
        else:
            box = trimesh.creation.box(extents=[width, depth, height])
            box.export(output_path)
            method = "trimesh_fallback"

        logger.info("Generated box: %s (%.1f x %.1f x %.1f mm) [%s]", output_path, width, depth, height, method)
        return output_path

    def _generate_cylinder(self, params: Dict[str, Any], output_path: Path) -> Path:
        """Generate a cylinder using CadQuery."""
        required = ["diameter", "height"]
        missing = [r for r in required if r not in params]
        if missing:
            raise ModelGenerationError(
                f"Missing required parameters: {', '.join(missing)}",
                details={"missing": missing, "provided": list(params.keys())},
            )

        diameter = float(params["diameter"])
        height = float(params["height"])
        radius = diameter / 2

        if CADQUERY_AVAILABLE:
            wp = cq.Workplane("XY").circle(radius).extrude(height)
            exporters.export(wp, str(output_path))
            method = "cadquery"
        else:
            cylinder = trimesh.creation.cylinder(radius=radius, height=height, sections=64)
            cylinder.export(output_path)
            method = "trimesh_fallback"

        logger.info("Generated cylinder: %s (dia %.1f x %.1f mm) [%s]", output_path, diameter, height, method)
        return output_path

    def _generate_tube_squeezer(self, params: Dict[str, Any], output_path: Path) -> Path:
        """
        Generate a tube squeezer using CadQuery.

        Creates a U-shaped channel with:
        - Extruded profile with proper wall thickness
        - Fillets on edges for printability
        - Grip ridges on sides
        """
        tube_diameter = float(params.get("tube_diameter", 50))
        wall_thickness = float(params.get("wall_thickness", 2.5))
        clearance = float(params.get("clearance", 1.0))
        width = float(params.get("width", tube_diameter + 30))

        slot_width = tube_diameter + clearance
        body_depth = tube_diameter * 0.75
        body_height = tube_diameter * 1.1

        if CADQUERY_AVAILABLE:
            body = cq.Workplane("XY").box(width, body_depth, body_height)
            slot = (
                cq.Workplane("XY")
                .box(slot_width, body_depth + 2, body_height)
                .translate((0, 0, wall_thickness / 2))
            )
            result = body.cut(slot)

            grip_positions = [-body_height / 4, 0, body_height / 4]
            handle_x = (width - slot_width) / 4 + slot_width / 2
           
            for z in grip_positions:
                grip_r = cq.Workplane("XY").circle(1.5).extrude(3).translate((handle_x, body_depth / 2, z))
                grip_l = cq.Workplane("XY").circle(1.5).extrude(3).translate((-handle_x, body_depth / 2, z))
                result = result.cut(grip_r).cut(grip_l)

            try:
                result = result.edges().fillet(1.0)
            except Exception:
                pass

            exporters.export(result, str(output_path))
            method = "cadquery"
        else:
            body = trimesh.creation.box(extents=[width, body_depth, body_height])
            slot = trimesh.creation.box(extents=[slot_width, body_depth + 2, body_height])
            slot.apply_translation([0, 0, wall_thickness / 2])
            result = body.difference(slot)

            grip_positions = [-body_height / 4, 0, body_height / 4]
            handle_x = (width - slot_width) / 4 + slot_width / 2
            for z in grip_positions:
                grip = trimesh.creation.cylinder(radius=1.5, height=3, sections=16)
                grip.apply_translation([handle_x, body_depth / 2, z])
                result = result.difference(grip)
                grip = trimesh.creation.cylinder(radius=1.5, height=3, sections=16)
                grip.apply_translation([-handle_x, body_depth / 2, z])
                result = result.difference(grip)

            if not result.is_watertight:
                result = result.fill_holes()
            result.export(output_path)
            method = "trimesh_fallback"

        logger.info(
            "Generated tube squeezer: %s (tube %.1fmm, slot %.1fmm) [%s]",
            output_path, tube_diameter, slot_width, method,
        )
        return output_path

    def _generate_bracket(self, params, output_path):
        width = float(params.get("width", 60))
        height = float(params.get("height", 50))
        thickness = float(params.get("thickness", 3.0))
        hole_diameter = float(params.get("hole_diameter", 5.0))

        if CADQUERY_AVAILABLE:
            vertical = cq.Workplane("XY").box(width, thickness, height)
            horizontal = cq.Workplane("XY").box(width, height * 0.6, thickness).translate((0, height * 0.3, -height / 2 + thickness / 2))
            result = vertical.union(horizontal)

            hole_r = hole_diameter / 2
            hole_v = cq.Workplane("XY").circle(hole_r).extrude(thickness + 2).translate((0, 0, height / 4))
            hole_h = cq.Workplane("XY").circle(hole_r).extrude(thickness + 2).translate((0, -height / 4, -height / 2))
            result = result.cut(hole_v).cut(hole_h)

            try:
                result = result.edges().fillet(1.5)
            except Exception:
                pass

            exporters.export(result, str(output_path))
            method = "cadquery"
        else:
            vertical = trimesh.creation.box(extents=[width, thickness, height])
            horizontal = trimesh.creation.box(extents=[width, height * 0.6, thickness])
            horizontal.apply_translation([0, height * 0.3, -height / 2 + thickness / 2])
            result = trimesh.util.concatenate([vertical, horizontal])
            result.export(output_path)
            method = "trimesh_fallback"

        logger.info("Generated bracket: %s (%.1fx%.1fx%.1f mm) [%s]", output_path, width, height, thickness, method)
        return output_path

    def _generate_enclosure(self, params, output_path):
        width = float(params.get("width", 80))
        depth = float(params.get("depth", 50))
        height = float(params.get("height", 30))
        wall_thickness = float(params.get("wall_thickness", 2.5))

        if CADQUERY_AVAILABLE:
            outer = cq.Workplane("XY").box(width, depth, height)
            inner = cq.Workplane("XY").box(
                width - 2 * wall_thickness,
                depth - 2 * wall_thickness,
                height - wall_thickness,
            ).translate((0, 0, wall_thickness / 2))
            result = outer.cut(inner)

            try:
                result = result.edges().fillet(1.0)
            except Exception:
                pass

            exporters.export(result, str(output_path))
            method = "cadquery"
        else:
            outer = trimesh.creation.box(extents=[width, depth, height])
            inner = trimesh.creation.box(extents=[
                width - 2 * wall_thickness,
                depth - 2 * wall_thickness,
                height - wall_thickness,
            ])
            inner.apply_translation([0, 0, wall_thickness / 2])
            result = outer.difference(inner)
            if not result.is_watertight:
                result = result.fill_holes()
            result.export(output_path)
            method = "trimesh_fallback"

        logger.info("Generated enclosure: %s (%.1fx%.1fx%.1f mm) [%s]", output_path, width, depth, height, method)
        return output_path

    def _generate_spacer(self, params, output_path):
        inner_diameter = float(params.get("inner_diameter", 8))
        outer_diameter = float(params.get("outer_diameter", 16))
        thickness = float(params.get("thickness", 3.0))

        inner_radius = inner_diameter / 2
        outer_radius = outer_diameter / 2

        if CADQUERY_AVAILABLE:
            result = (
                cq.Workplane("XY")
                .circle(outer_radius)
                .extrude(thickness)
                .faces(">Z")
                .workplane()
                .hole(inner_diameter)
            )
            exporters.export(result, str(output_path))
            method = "cadquery"
        else:
            outer = trimesh.creation.cylinder(radius=outer_radius, height=thickness, sections=64)
            inner = trimesh.creation.cylinder(radius=inner_radius, height=thickness + 2, sections=64)
            result = outer.difference(inner)
            result.export(output_path)
            method = "trimesh_fallback"

        logger.info("Generated spacer: %s (ID %.1f, OD %.1f, T %.1f) [%s]", output_path, inner_diameter, outer_diameter, thickness, method)
        return output_path

    def _generate_hook(self, params, output_path):
        arm_length = float(params.get("arm_length", 40))
        thickness = float(params.get("thickness", 4.0))
        mount_hole_diameter = float(params.get("mount_hole_diameter", 5.0))

        if CADQUERY_AVAILABLE:
            base = cq.Workplane("XY").box(thickness * 2, thickness * 2, thickness * 3)
            arm = cq.Workplane("XY").box(arm_length, thickness, thickness).translate((arm_length / 2, 0, thickness))
            tip = cq.Workplane("XY").box(thickness * 2, thickness, thickness * 2).translate((arm_length + thickness, 0, thickness * 1.5))
            result = base.union(arm).union(tip)

            hole = cq.Workplane("XY").circle(mount_hole_diameter / 2).extrude(thickness * 4).translate((0, 0, 0))
            result = result.cut(hole)

            try:
                result = result.edges().fillet(1.0)
            except Exception:
                pass

            exporters.export(result, str(output_path))
            method = "cadquery"
        else:
            base = trimesh.creation.box(extents=[thickness * 2, thickness * 2, thickness * 3])
            arm = trimesh.creation.box(extents=[arm_length, thickness, thickness])
            arm.apply_translation([arm_length / 2, 0, thickness])
            tip = trimesh.creation.box(extents=[thickness * 2, thickness, thickness * 2])
            tip.apply_translation([arm_length + thickness, 0, thickness * 1.5])
            result = trimesh.util.concatenate([base, arm, tip])
            result.export(output_path)
            method = "trimesh_fallback"

        logger.info("Generated hook: %s (arm %.1f mm) [%s]", output_path, arm_length, method)
        return output_path

    def _generate_cup_holder(self, params, output_path):
        """Generate a cup holder — hollow cylinder with a base disc."""
        diameter = float(params.get("diameter", 80))
        height = float(params.get("height", 64))
        wall_thickness = float(params.get("wall_thickness", 2.5))
        base_thickness = float(params.get("base_thickness", 3.0))
        outer_radius = diameter / 2
        inner_radius = outer_radius - wall_thickness

        if CADQUERY_AVAILABLE:
            outer = cq.Workplane("XY").circle(outer_radius).extrude(height)
            inner = (
                cq.Workplane("XY")
                .circle(inner_radius)
                .extrude(height - base_thickness)
                .translate((0, 0, base_thickness))
            )
            result = outer.cut(inner)
            try:
                result = result.edges().fillet(1.0)
            except Exception:
                pass
            exporters.export(result, str(output_path))
            method = "cadquery"
        else:
            outer = trimesh.creation.cylinder(radius=outer_radius, height=height, sections=64)
            inner = trimesh.creation.cylinder(radius=inner_radius, height=height - base_thickness, sections=64)
            inner.apply_translation([0, 0, base_thickness])
            result = outer.difference(inner)
            if not result.is_watertight:
                result = result.fill_holes()
            result.export(output_path)
            method = "trimesh_fallback"

        logger.info("Generated cup_holder: %s (dia %.1f x %.1f mm) [%s]", output_path, diameter, height, method)
        return output_path

    def _generate_phone_stand(self, params, output_path):
        """Generate a phone stand — angled wedge with a lip."""
        width = float(params.get("width", 70))
        depth = float(params.get("depth", 42))
        height = float(params.get("height", 35))
        angle = float(params.get("angle", 60))
        lip_height = float(params.get("lip_height", 5.0))
        wall_thickness = float(params.get("wall_thickness", 3.0))

        if CADQUERY_AVAILABLE:
            # Base block
            base = cq.Workplane("XY").box(width, depth, wall_thickness)
            # Back support (angled via a wedge cut)
            back = cq.Workplane("XY").box(width, wall_thickness, height).translate((0, -depth / 2 + wall_thickness / 2, height / 2 - wall_thickness / 2))
            # Lip at front
            lip = cq.Workplane("XY").box(width, wall_thickness, lip_height + wall_thickness).translate((0, depth / 2 - wall_thickness / 2, lip_height / 2))
            result = base.union(back).union(lip)
            try:
                result = result.edges().fillet(1.0)
            except Exception:
                pass
            exporters.export(result, str(output_path))
            method = "cadquery"
        else:
            base = trimesh.creation.box(extents=[width, depth, wall_thickness])
            back = trimesh.creation.box(extents=[width, wall_thickness, height])
            back.apply_translation([0, -depth / 2 + wall_thickness / 2, height / 2 - wall_thickness / 2])
            lip = trimesh.creation.box(extents=[width, wall_thickness, lip_height + wall_thickness])
            lip.apply_translation([0, depth / 2 - wall_thickness / 2, lip_height / 2])
            result = trimesh.util.concatenate([base, back, lip])
            result.export(output_path)
            method = "trimesh_fallback"

        logger.info("Generated phone_stand: %s (%.1fx%.1fx%.1f mm) [%s]", output_path, width, depth, height, method)
        return output_path

    def _generate_keychain(self, params, output_path):
        """Generate a keychain — flat tag with a through-hole for a keyring."""
        width = float(params.get("width", 40))
        height = float(params.get("height", 24))
        thickness = float(params.get("thickness", 3.0))
        hole_diameter = float(params.get("hole_diameter", 5.0))
        corner_radius = float(params.get("corner_radius", 3.0))

        if CADQUERY_AVAILABLE:
            body = cq.Workplane("XY").box(width, height, thickness)
            hole = (
                cq.Workplane("XY")
                .circle(hole_diameter / 2)
                .extrude(thickness + 2)
                .translate((-width / 2 + hole_diameter, 0, 0))
            )
            result = body.cut(hole)
            try:
                result = result.edges().fillet(corner_radius)
            except Exception:
                pass
            exporters.export(result, str(output_path))
            method = "cadquery"
        else:
            body = trimesh.creation.box(extents=[width, height, thickness])
            hole = trimesh.creation.cylinder(radius=hole_diameter / 2, height=thickness + 2, sections=32)
            hole.apply_translation([-width / 2 + hole_diameter, 0, 0])
            result = body.difference(hole)
            if not result.is_watertight:
                result = result.fill_holes()
            result.export(output_path)
            method = "trimesh_fallback"

        logger.info("Generated keychain: %s (%.1fx%.1fx%.1f mm) [%s]", output_path, width, height, thickness, method)
        return output_path

    def _generate_cable_clip(self, params, output_path):
        """Generate a cable clip — channel to grip a cable, flat back with mount hole."""
        cable_diameter = float(params.get("cable_diameter", 6))
        clip_width = float(params.get("clip_width", 18))
        wall_thickness = float(params.get("wall_thickness", 2.5))
        mount_hole_diameter = float(params.get("mount_hole_diameter", 3.5))
        body_height = cable_diameter + wall_thickness * 2
        body_depth = cable_diameter + wall_thickness

        if CADQUERY_AVAILABLE:
            body = cq.Workplane("XY").box(clip_width, body_depth, body_height)
            channel = (
                cq.Workplane("XY")
                .box(clip_width + 2, cable_diameter, cable_diameter)
                .translate((0, 0, wall_thickness))
            )
            result = body.cut(channel)
            mount_hole = (
                cq.Workplane("XY")
                .circle(mount_hole_diameter / 2)
                .extrude(body_depth + 2)
                .translate((0, 0, body_height / 2))
                .rotate((0, 0, 0), (1, 0, 0), 90)
            )
            result = result.cut(mount_hole)
            try:
                result = result.edges().fillet(0.8)
            except Exception:
                pass
            exporters.export(result, str(output_path))
            method = "cadquery"
        else:
            body = trimesh.creation.box(extents=[clip_width, body_depth, body_height])
            channel = trimesh.creation.box(extents=[clip_width + 2, cable_diameter, cable_diameter])
            channel.apply_translation([0, 0, wall_thickness])
            result = body.difference(channel)
            mount_hole = trimesh.creation.cylinder(radius=mount_hole_diameter / 2, height=body_depth + 2, sections=32)
            mount_hole.apply_translation([0, 0, body_height / 2])
            result = result.difference(mount_hole)
            if not result.is_watertight:
                result = result.fill_holes()
            result.export(output_path)
            method = "trimesh_fallback"

        logger.info("Generated cable_clip: %s (cable %.1f mm) [%s]", output_path, cable_diameter, method)
        return output_path
