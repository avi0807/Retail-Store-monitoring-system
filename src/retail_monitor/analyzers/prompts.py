"""Prompt templates kept separate from analyzer logic for easier iteration."""

from __future__ import annotations

CLEANLINESS_PROMPT = """You are an expert facility maintenance inspector analyzing a retail store image for cleanliness.

**DETECTED OBJECTS (from open-vocabulary YOLO):**
{detections}

**CONTEXT:**
- Space type: {space_type}
- Traffic level: {traffic_level}
- Hours since last cleaning: {hours_since_cleaned:.1f}

**YOUR TASK:**
Carefully examine this image and provide a detailed cleanliness assessment.

Look for:
1. Floor condition: debris, spills, stains, scuff marks.
2. Spatial analysis for each detected object: floor vs shelf, correct location, should it be there.
3. Severity 0-10: 0-2 pristine, 3-4 very clean, 5-6 acceptable, 7-8 needs cleaning soon, 9-10 immediate.

Guidelines: trust what you SEE over YOLO labels. Don't confuse shadows with dirt. Be practical.

Respond with ONLY valid JSON. No prose, no code fences. Each item in floor_objects, shelf_objects, and misplaced_items MUST be an object with keys.

{{
    "cleanliness_analysis": {{
        "overall_cleanliness_score": 8.5,
        "floor_condition": "clean",
        "visible_debris": ["dust"],
        "debris_locations": ["corner"],
        "spills_present": false,
        "stains_present": false,
        "reasoning": "..."
    }},
    "spatial_analysis": {{
        "floor_objects": [
            {{"object": "bottle", "location": "center aisle", "should_be_here": false, "concern_level": "medium"}}
        ],
        "shelf_objects": [
            {{"object": "product", "location": "shelf 2", "properly_placed": true}}
        ],
        "misplaced_items": [
            {{"object": "box", "current_location": "floor", "should_be": "shelf"}}
        ],
        "spatial_reasoning": "..."
    }}
}}
"""


MERCHANDISE_PROMPT = """You are a retail merchandising expert analyzing shelf presentation.

**DETECTED OBJECTS:**
{detections}

**EXPECTED SHELF FULLNESS:** {expected_fullness}%

Assess shelf fullness, organization, empty spaces, misplaced products, and fallen products.

Respond with ONLY valid JSON:

{{
    "shelf_fullness_score": 0,
    "shelf_organization_score": 0,
    "empty_spaces_count": 0,
    "misplaced_products_count": 0,
    "fallen_products_count": 0,
    "reasoning": "..."
}}
"""


DECISION_PROMPT = """You are a retail operations manager making alert decisions.

**ANALYSIS TYPE:** {decision_type}
**ANALYSIS DATA:**
{analysis}
**CONTEXT:**
{context}

Cleanliness guidelines: 0-4 no alert, 5-6 monitor, 7-8 alert soon, 9-10 immediate.
Merchandise guidelines: fallen products = immediate alert, fullness < 60% = restock alert, organization < 5 = alert.

Respond with ONLY valid JSON:
{{
    "alert_required": true,
    "priority": "medium",
    "reasoning": "...",
    "recommended_action": "...",
    "estimated_time_minutes": 15,
    "confidence_level": 0.85
}}
"""
