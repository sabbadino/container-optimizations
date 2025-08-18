class CombinedStoppingCriterion:
    """Combines multiple stopping criteria - stops when ANY criterion is met."""

    def __init__(self, *criteria):
        self.criteria = criteria

    def __call__(self, rng, best, current):
        """Return True if any of the criteria say to stop."""
        return any(criterion(rng, best, current) for criterion in self.criteria)


class StoppingCriterionWithProgress:
    """
    A custom stopping criterion that wraps other criteria and prints progress.
    """

    def __init__(self, max_iterations, max_no_improve):
        self.max_iterations = max_iterations
        self.max_no_improve = max_no_improve
        self.iteration = 0
        self.no_improve = 0

    def __call__(self, rng, best, current):
        self.iteration += 1

        # Check if the best solution has improved
        if best.objective() < getattr(self, '_last_best_obj', float('inf')):
            self._last_best_obj = best.objective()
            self.no_improve = 0
        else:
            self.no_improve += 1

        # Print progress
        progress_bar = f"Iteration {self.iteration}/{self.max_iterations} | "
        progress_bar += f"No improvement {self.no_improve}/{self.max_no_improve}"
        print(progress_bar)  # Use carriage return to print on the same line

        # Check stopping conditions
        if self.iteration >= self.max_iterations:
            print("\nStopping: Max iterations reached.")
            return True
        if self.no_improve >= self.max_no_improve:
            print("\nStopping: Max no improvement reached.")
            return True

        return False
