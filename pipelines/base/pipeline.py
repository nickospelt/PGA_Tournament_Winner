from typing import List, Dict, Any, Optional
import graphlib
from .task import Task

class Pipeline:
    """
    Orchestrates a series of Tasks based on their dependencies.

    Automatically sorts tasks using a topological sort (Directed Acyclic Graph).
    Manages a shared context that tasks can read from and write to.

    Attributes:
        name (str): The name of the pipeline for logging and identification.
        tasks (List[Task]): The list of tasks currently added to the pipeline.
    """

    def __init__(self, name: str, tasks: Optional[List[Task]] = None):
        """
        Initializes a new Pipeline.

        Args:
            name (str): The name of the pipeline.
            tasks (Optional[List[Task]]): An optional list of tasks to include.
                Defaults to an empty list.
        """
        self.name = name
        self.tasks = tasks or []

    def add_task(self, task: Task):
        """
        Adds a single task to the pipeline.

        Args:
            task (Task): The task to add to the pipeline.
        """
        self.tasks.append(task)

    def _get_execution_order(self) -> List[Task]:
        """
        Builds the dependency graph and returns tasks in topological order.

        Performs a topological sort on the pipeline's tasks based on their
        declared dependencies.

        Returns:
            List[Task]: A list of Task objects in the order they should be executed.

        Raises:
            graphlib.CycleError: If a circular dependency is detected in the pipeline.
        """
        # Map task names/objects to their dependencies
        # graphlib expects {node: [predecessors]}
        graph = {}
        
        for task in self.tasks:
            # Only include dependencies that are actually in the pipeline
            deps = [dep for dep in task.dependencies if dep in self.tasks]
            
            # Check for dependencies that are NOT in the pipeline
            missing_deps = [dep for dep in task.dependencies if dep not in self.tasks]
            if missing_deps:
                print(f"Warning: Task '{task.name}' depends on tasks not in the pipeline: "
                      f"{[d.name for d in missing_deps]}")
            
            graph[task] = deps

        ts = graphlib.TopologicalSorter(graph)
        try:
            return list(ts.static_order())
        except graphlib.CycleError as e:
            print(f"Error: Circular dependency detected in pipeline '{self.name}': {e}")
            raise

    def run(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Runs tasks in their determined topological order.

        Orchestrates the execution of each task, passing and updating the
        shared context between them.

        Args:
            initial_context (Optional[Dict[str, Any]]): An optional initial state
                for the pipeline context. Defaults to an empty dictionary.

        Returns:
            Dict[str, Any]: The final state of the shared context after all
                tasks have completed.
        """
        print(f"=== Starting DAG pipeline: {self.name} ===")
        
        execution_order = self._get_execution_order()
        context = initial_context or {}

        for task in execution_order:
            result = task.run(context)

            if result:
                context.update(result)

        print(f"=== Pipeline {self.name} completed. ===")
        return context
