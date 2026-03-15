from typing import Dict, Any, Optional, List
from pipelines.base.task import Task

class ProvideSpecificTournamentsTask(Task):
    """
    Injects a specific list of tournament IDs into the pipeline context.

    This task is used when the user manually provides tournament IDs 
    instead of determining them from the ESPN schedule.

    Attributes:
        tournament_ids (List[int]): The list of tournament IDs to process.
    """

    def __init__(self, name: str, tournament_ids: List[int]):
        """
        Initializes the ProvideSpecificTournamentsTask.

        Args:
            name (str): The name of the task.
            tournament_ids (List[int]): List of tournament IDs.
        """
        super().__init__(name)
        self.tournament_ids = tournament_ids

    def execute(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes the injection of tournament IDs.

        Args:
            context (Dict[str, Any]): The shared pipeline context.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing 'tournament_ids'.
        """
        print(f"Provided {len(self.tournament_ids)} specific tournament IDs.")
        return {"tournament_ids": self.tournament_ids}
