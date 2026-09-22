"""
Tube Squeezer Generator - Specialized generator for tube squeezer models.

Stub implementation for Phase 2 stabilization.
Full CadQuery integration will be completed in Phase 3.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from vibe_print.exceptions import ModelGenerationError, InputValidationError
from vibe_print.logging_config import get_logger, log_duration, summarize_input

logger = get_logger(__name__)


class TubeSqueezerGenerator:
    """
    Generate tube squeezer / toothpaste squeezer models.

    Stub implementation that delegates to ParametricGenerator.
    In Phase 3, this will have dedicated CadQuery geometry for
    optimized tube squeezer designs.
    """

    def __init__(self):
        from vibe_print.generator.cad_generator import ParametricGenerator

        self._generator = ParametricGenerator()

    def generate(
        self,
        tube_diameter: float,
        wall_thickness: float = 2.0,
        width: float = 40.0,
        handle_length: float = 30.0,
        clearance: float = 0.3,
        add_grip_texture: bool = False,
        output_name: Optional[str] = None,
    ) -> str:
        """
        Generate a tube squeezer model.

        Args:
            tube_diameter: Diameter of the tube in mm
            wall_thickness: Thickness of the squeezer walls in mm
            width: Width of the squeezer body in mm
            handle_length: Length of the handle in mm
            clearance: Gap between moving parts in mm
            add_grip_texture: Whether to add grip texture
            output_name: Optional output filename

        Returns:
            Path to the generated STL file

        Raises:
            InputValidationError: If parameters are invalid
            ModelGenerationError: If generation fails
        """
        with log_duration(logger, "generate_tube_squeezer"):
            logger.info(
                "Generating tube squeezer | %s",
                summarize_input(
                    tube_diameter=tube_diameter,
                    wall_thickness=wall_thickness,
                    width=width,
                ),
            )

            # Input validation
            if tube_diameter <= 0:
                raise InputValidationError(
                    "tube_diameter must be positive",
                    details={"tube_diameter": tube_diameter},
                )
            if wall_thickness <= 0:
                raise InputValidationError(
                    "wall_thickness must be positive",
                    details={"wall_thickness": wall_thickness},
                )
            if width <= 0:
                raise InputValidationError(
                    "width must be positive",
                    details={"width": width},
                )
            if clearance < 0:
                raise InputValidationError(
                    "clearance must be non-negative",
                    details={"clearance": clearance},
                )

            parameters = {
                "tube_diameter": tube_diameter,
                "wall_thickness": wall_thickness,
                "width": width,
                "handle_length": handle_length,
                "clearance": clearance,
                "add_grip_texture": add_grip_texture,
            }

            name = output_name or "tube_squeezer"
            return self._generator.generate(
                model_type="tube_squeezer",
                parameters=parameters,
                output_name=name,
            )
