"""Local Qwen2.5-VL backed implementation of the VisionAnalyzer protocol.

Reuses the Gemini analyzer's prompts and JSON parser so prompt
changes propagate to both backends. Heavy dependencies (torch,
transformers, pillow) are imported lazily and live behind the
``[local]`` install extra.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import cv2
import numpy as np

from retail_monitor.analyzers.json_utils import parse_json_response, sanitize_items_list
from retail_monitor.analyzers.prompts import (
    CLEANLINESS_PROMPT,
    DECISION_PROMPT,
    MERCHANDISE_PROMPT,
)
from retail_monitor.models import (
    AlertDecision,
    AlertPriority,
    AnalysisContext,
    CleanlinessAnalysis,
    MerchandiseAnalysis,
    SpatialAnalysis,
    YOLODetection,
)

logger = logging.getLogger(__name__)


_DEFAULT_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"


class QwenVisionAnalyzer:
    """Local Qwen2.5-VL implementation of the VisionAnalyzer protocol."""

    def __init__(
        self,
        model_id: str = _DEFAULT_MODEL,
        device: str = "auto",
        dtype: str = "auto",
        max_new_tokens: int = 1024,
        load_in_4bit: bool = False,
    ) -> None:
        try:
            import torch
            from transformers import (
                AutoProcessor,
                Qwen2_5_VLForConditionalGeneration,
            )
        except ImportError as exc:
            raise RuntimeError(
                "QwenVisionAnalyzer requires torch + transformers. "
                "Install with: pip install '.[local]'"
            ) from exc

        self.model_id = model_id
        self.max_new_tokens = max_new_tokens

        torch_dtype = self._resolve_dtype(dtype, torch)
        device_map = "auto" if device == "auto" else device

        load_kwargs: dict[str, Any] = {
            "torch_dtype": torch_dtype,
            "device_map": device_map,
        }
        if load_in_4bit:
            load_kwargs["load_in_4bit"] = True

        logger.info("Loading Qwen2.5-VL model: %s", model_id)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id, **load_kwargs
        )
        self.processor = AutoProcessor.from_pretrained(model_id)
        self._torch = torch
        logger.info("Qwen2.5-VL ready (device_map=%s, dtype=%s)", device_map, torch_dtype)

    def analyze_cleanliness(
        self,
        image: np.ndarray,
        detections: list[YOLODetection],
        context: AnalysisContext,
    ) -> tuple[CleanlinessAnalysis, SpatialAnalysis]:
        prompt = CLEANLINESS_PROMPT.format(
            detections=self._format_detections(detections),
            space_type=context.space_type.value,
            traffic_level=context.traffic_level.value,
            hours_since_cleaned=context.hours_since_cleaned,
        )
        try:
            data = self._invoke_with_image(prompt, image)
            cleanliness = CleanlinessAnalysis(
                overall_cleanliness_score=float(
                    data["cleanliness_analysis"]["overall_cleanliness_score"]
                ),
                floor_condition=data["cleanliness_analysis"]["floor_condition"],
                visible_debris=list(data["cleanliness_analysis"].get("visible_debris", [])),
                debris_locations=list(data["cleanliness_analysis"].get("debris_locations", [])),
                spills_present=bool(data["cleanliness_analysis"].get("spills_present", False)),
                stains_present=bool(data["cleanliness_analysis"].get("stains_present", False)),
                reasoning=data["cleanliness_analysis"].get("reasoning", ""),
            )
            spatial_raw = data.get("spatial_analysis", {})
            spatial = SpatialAnalysis(
                floor_objects=sanitize_items_list(spatial_raw.get("floor_objects", [])),
                shelf_objects=sanitize_items_list(spatial_raw.get("shelf_objects", [])),
                misplaced_items=sanitize_items_list(spatial_raw.get("misplaced_items", [])),
                spatial_reasoning=spatial_raw.get("spatial_reasoning", ""),
            )
            return cleanliness, spatial
        except Exception as exc:
            logger.exception("Cleanliness analysis failed, using fallback: %s", exc)
            return self._fallback_cleanliness(), SpatialAnalysis()

    def analyze_merchandise(
        self,
        image: np.ndarray,
        detections: list[YOLODetection],
        context: AnalysisContext,
    ) -> MerchandiseAnalysis:
        prompt = MERCHANDISE_PROMPT.format(
            detections=self._format_detections(detections),
            expected_fullness=context.expected_shelf_fullness,
        )
        try:
            data = self._invoke_with_image(prompt, image)
            return MerchandiseAnalysis(
                shelf_fullness_score=float(data["shelf_fullness_score"]),
                shelf_organization_score=float(data["shelf_organization_score"]),
                empty_spaces_count=int(data.get("empty_spaces_count", 0)),
                misplaced_products_count=int(data.get("misplaced_products_count", 0)),
                fallen_products_count=int(data.get("fallen_products_count", 0)),
                reasoning=data.get("reasoning", ""),
            )
        except Exception as exc:
            logger.exception("Merchandise analysis failed, using fallback: %s", exc)
            return MerchandiseAnalysis(
                shelf_fullness_score=5.0,
                shelf_organization_score=5.0,
                reasoning="Fallback - VLM error.",
            )

    def make_alert_decision(
        self,
        cleanliness: CleanlinessAnalysis | None,
        spatial: SpatialAnalysis | None,
        merchandise: MerchandiseAnalysis | None,
        context: AnalysisContext,
    ) -> AlertDecision:
        if cleanliness is not None:
            decision_type = "cleanliness"
            analysis: dict[str, Any] = {
                "cleanliness_score": cleanliness.overall_cleanliness_score,
                "floor_condition": cleanliness.floor_condition,
                "visible_debris": cleanliness.visible_debris,
                "spills_present": cleanliness.spills_present,
                "stains_present": cleanliness.stains_present,
                "reasoning": cleanliness.reasoning,
            }
            if spatial is not None:
                analysis["floor_objects_count"] = len(spatial.floor_objects)
                analysis["misplaced_items_count"] = len(spatial.misplaced_items)
        elif merchandise is not None:
            decision_type = "merchandise"
            analysis = {
                "shelf_fullness": merchandise.shelf_fullness_score,
                "shelf_organization": merchandise.shelf_organization_score,
                "empty_spaces": merchandise.empty_spaces_count,
                "fallen_products": merchandise.fallen_products_count,
                "reasoning": merchandise.reasoning,
            }
        else:
            return self._fallback_decision()

        ctx = {
            "space_type": context.space_type.value,
            "traffic_level": context.traffic_level.value,
            "store_tier": context.store_tier,
            "hours_since_cleaned": context.hours_since_cleaned,
        }

        prompt = DECISION_PROMPT.format(
            decision_type=decision_type,
            analysis=json.dumps(analysis, indent=2, default=str),
            context=json.dumps(ctx, indent=2),
        )

        try:
            data = self._invoke_text_only(prompt)
            return AlertDecision(
                alert_required=bool(data["alert_required"]),
                priority=AlertPriority(data["priority"]),
                reasoning=data.get("reasoning", ""),
                recommended_action=data.get("recommended_action", ""),
                estimated_time_minutes=int(data.get("estimated_time_minutes", 0)),
                confidence_level=float(data.get("confidence_level", 0.0)),
            )
        except Exception as exc:
            logger.exception("Alert decision failed, using rule-based fallback: %s", exc)
            score = cleanliness.overall_cleanliness_score if cleanliness else None
            return self._fallback_decision(score)

    def _invoke_with_image(self, prompt: str, image: np.ndarray) -> dict[str, Any]:
        from PIL import Image

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        return parse_json_response(self._generate(messages))

    def _invoke_text_only(self, prompt: str) -> dict[str, Any]:
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ]
        return parse_json_response(self._generate(messages))

    def _generate(self, messages: list[dict[str, Any]]) -> str:
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs = [
            block["image"]
            for msg in messages
            for block in msg["content"]
            if isinstance(block, dict) and block.get("type") == "image"
        ] or None

        inputs = self.processor(
            text=[text],
            images=image_inputs,
            padding=True,
            return_tensors="pt",
        ).to(self.model.device)

        with self._torch.inference_mode():
            generated = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )

        # Drop the prompt tokens; only decode the new completion.
        trimmed = [out[len(inp):] for inp, out in zip(inputs.input_ids, generated)]
        decoded = self.processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        return decoded[0] if decoded else ""

    @staticmethod
    def _format_detections(detections: list[YOLODetection]) -> str:
        if not detections:
            return "No objects detected"
        counts: dict[str, int] = {}
        for d in detections:
            counts[d.class_name] = counts.get(d.class_name, 0) + 1
        return "\n".join(f"- {n}x {label}" for label, n in counts.items())

    @staticmethod
    def _resolve_dtype(dtype: str, torch_module):
        if dtype == "auto":
            return "auto"
        return getattr(torch_module, dtype)

    @staticmethod
    def _encode_image_b64(image: np.ndarray) -> str:
        ok, buffer = cv2.imencode(".jpg", image)
        if not ok:
            raise RuntimeError("Failed to encode image to JPEG")
        return base64.b64encode(buffer).decode("utf-8")

    @staticmethod
    def _fallback_cleanliness() -> CleanlinessAnalysis:
        return CleanlinessAnalysis(
            overall_cleanliness_score=5.0,
            floor_condition="unknown",
            reasoning="Fallback - VLM error.",
        )

    @staticmethod
    def _fallback_decision(score: float | None = None) -> AlertDecision:
        # Score is 0-10 where 10 is pristine: lower = dirtier.
        if score is not None:
            if score < 4:
                return AlertDecision(
                    alert_required=True,
                    priority=AlertPriority.HIGH,
                    reasoning=f"Score {score:.1f}/10 (rule-based fallback).",
                    recommended_action="Clean immediately.",
                    estimated_time_minutes=15,
                    confidence_level=0.6,
                )
            if score < 6:
                return AlertDecision(
                    alert_required=True,
                    priority=AlertPriority.MEDIUM,
                    reasoning=f"Score {score:.1f}/10 (rule-based fallback).",
                    recommended_action="Schedule cleaning.",
                    estimated_time_minutes=10,
                    confidence_level=0.6,
                )
            return AlertDecision(
                alert_required=False,
                priority=AlertPriority.NONE,
                reasoning=f"Score {score:.1f}/10 - acceptable (fallback).",
                recommended_action="Continue normal schedule.",
                estimated_time_minutes=0,
                confidence_level=0.6,
            )
        return AlertDecision(
            alert_required=False,
            priority=AlertPriority.NONE,
            reasoning="VLM error - manual review required.",
            recommended_action="Manual inspection.",
            estimated_time_minutes=0,
            confidence_level=0.0,
        )
