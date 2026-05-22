"""Domain models for the retail monitoring system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SpaceType(str, Enum):
    AISLE = "aisle"
    ENTRANCE = "entrance"
    CHECKOUT = "checkout"
    BACKROOM = "backroom"
    PRODUCE = "produce"
    DELI = "deli"


class TrafficLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass
class YOLODetection:
    class_name: str
    confidence: float
    bbox: list[float]


@dataclass
class CleanlinessAnalysis:
    overall_cleanliness_score: float
    floor_condition: str
    visible_debris: list[str] = field(default_factory=list)
    debris_locations: list[str] = field(default_factory=list)
    spills_present: bool = False
    stains_present: bool = False
    reasoning: str = ""


@dataclass
class SpatialAnalysis:
    floor_objects: list[dict[str, Any]] = field(default_factory=list)
    shelf_objects: list[dict[str, Any]] = field(default_factory=list)
    misplaced_items: list[dict[str, Any]] = field(default_factory=list)
    spatial_reasoning: str = ""


@dataclass
class MerchandiseAnalysis:
    shelf_fullness_score: float
    shelf_organization_score: float
    empty_spaces_count: int = 0
    misplaced_products_count: int = 0
    fallen_products_count: int = 0
    reasoning: str = ""


@dataclass
class AlertDecision:
    alert_required: bool
    priority: AlertPriority
    reasoning: str
    recommended_action: str
    estimated_time_minutes: int = 0
    confidence_level: float = 0.0


@dataclass
class AnalysisContext:
    space_type: SpaceType = SpaceType.AISLE
    traffic_level: TrafficLevel = TrafficLevel.MEDIUM
    store_tier: str = "standard"
    hours_since_cleaned: float = 3.0
    expected_shelf_fullness: float = 80.0
    camera_id: str | None = None
    location: str | None = None


@dataclass
class AnalysisResult:
    alert_decision: AlertDecision
    raw_detections: list[YOLODetection] = field(default_factory=list)
    cleanliness_analysis: CleanlinessAnalysis | None = None
    spatial_analysis: SpatialAnalysis | None = None
    merchandise_analysis: MerchandiseAnalysis | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    camera_id: str | None = None
    frame_index: int | None = None
