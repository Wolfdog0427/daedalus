"""
Hierarchical step generator for goals.
Deterministic, symbolic, and conservative.
"""

def generate_hierarchical_steps(goal_text: str):
    goal_text = goal_text.lower()

    # Workspace organization
    if "organize" in goal_text and "workspace" in goal_text:
        return [
            {
                "step": "Identify clutter zones",
                "substeps": [
                    "Desk surface",
                    "Shelves",
                    "Floor area",
                    "Drawers"
                ]
            },
            {
                "step": "Sort items into categories",
                "substeps": [
                    "Keep",
                    "Donate",
                    "Trash",
                    "Relocate"
                ]
            },
            {
                "step": "Clean surfaces",
                "substeps": [
                    "Wipe desk",
                    "Dust shelves",
                    "Vacuum floor"
                ]
            },
            {
                "step": "Reorganize essentials",
                "substeps": [
                    "Arrange tools",
                    "Place frequently used items within reach",
                    "Store rarely used items"
                ]
            }
        ]

    # Workout planning
    if "workout" in goal_text or "exercise" in goal_text:
        return [
            {
                "step": "Define fitness objectives",
                "substeps": [
                    "Strength",
                    "Endurance",
                    "Flexibility",
                    "Weight loss"
                ]
            },
            {
                "step": "Choose training schedule",
                "substeps": [
                    "Days per week",
                    "Session duration",
                    "Rest days"
                ]
            },
            {
                "step": "Select exercises",
                "substeps": [
                    "Upper body",
                    "Lower body",
                    "Core",
                    "Cardio"
                ]
            },
            {
                "step": "Plan progression",
                "substeps": [
                    "Increase reps",
                    "Increase weight",
                    "Increase duration"
                ]
            }
        ]

    # Default fallback
    return [
        {
            "step": "Clarify the goal",
            "substeps": [
                "Identify desired outcome",
                "Identify constraints",
                "Identify resources"
            ]
        },
        {
            "step": "Break goal into components",
            "substeps": [
                "List major tasks",
                "Group related tasks",
                "Identify dependencies"
            ]
        },
        {
            "step": "Create execution plan",
            "substeps": [
                "Order tasks",
                "Assign priorities",
                "Define checkpoints"
            ]
        }
    ]
