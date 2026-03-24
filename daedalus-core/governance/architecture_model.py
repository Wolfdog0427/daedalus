from typing import Dict, List


class ArchitectureModel:
    """
    Describes canonical structure, naming, and dependency rules.
    """

    def get_canonical_structure(self) -> Dict[str, List[str]]:
        # TODO: return directory/module layout
        return {}

    def validate_structure(self) -> List[str]:
        """
        Return list of structural issues.
        """
        return []
