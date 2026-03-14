from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Set

class Task(ABC):
    """
    Abstract Base Class for a single unit of work in a pipeline.

    Tasks can declare dependencies on other tasks that must run before them.
    Subclasses must implement the `execute` method.

    Attributes:
        name (str): The name of the task for logging and identification.
        dependencies (Set[Task]): A set of Task objects that this task depends on.
    """

    def __init__(self, name: str, depends_on: Optional[List['Task']] = None):
        """
        Initializes a new Task.

        Args:
            name (str): The name of the task.
            depends_on (Optional[List[Task]]): A list of tasks that must be completed
                before this task can run. Defaults to None.
        """
        self.name = name
        self.dependencies: Set['Task'] = set(depends_on or [])

    def run(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Template method for running a task.

        It handles common task-level logic (e.g., logging) and delegates
        the core logic to the `execute` method.

        Args:
            context (Dict[str, Any]): The shared pipeline context containing data
                from previous tasks.

        Returns:
            Optional[Dict[str, Any]]: A dictionary of results to be merged into
                the shared context, or None if no updates are needed.
        """
        print(f"--- Running task: {self.name} ---")
        return self.execute(context)

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        The core logic of the task to be implemented by subclasses.

        Args:
            context (Dict[str, Any]): The shared pipeline context.

        Returns:
            Optional[Dict[str, Any]]: New data to be added to the pipeline context.
        """
        pass

    def __repr__(self):
        """Returns a string representation of the Task."""
        return f"Task(name='{self.name}')"
