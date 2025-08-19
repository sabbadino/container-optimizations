import time


class CombinedStoppingCriterion:
    """Combines multiple stopping criteria - stops when ANY criterion is met."""

    def __init__(self, *criteria):
        self.criteria = criteria

    def __call__(self, rng, best, current):
        """Return True if any of the criteria say to stop."""
        return any(criterion(rng, best, current) for criterion in self.criteria)


class StoppingCriterionWithProgress:
    """
    Custom stopping criterion with progress printing.

    Stops when ANY of the following is met:
        - elapsed wall-clock time >= time_limit (seconds)
        - iteration count >= max_iterations
        - no-improvement iterations >= max_no_improve
    """

    def __init__(self, max_iterations, max_no_improve, time_limit):
        if time_limit is None:
            raise ValueError("time_limit must be provided (seconds) and cannot be None")
        self.max_iterations = int(max_iterations)
        self.max_no_improve = int(max_no_improve)
        self.time_limit = float(time_limit)
        self.start_time = time.time()
        self.iteration = 0
        self.no_improve = 0
        self._last_best_obj = float("inf")

    def __call__(self, rng, best, current):
        # Time-based stopping (checked first)
        elapsed = time.time() - self.start_time
        if elapsed >= self.time_limit:
            print("\nStopping: Time limit reached.")
            return True

        self.iteration += 1

        # Check if the best solution has improved
        if best.objective() < self._last_best_obj:
            self._last_best_obj = best.objective()
            self.no_improve = 0
        else:
            self.no_improve += 1

        # Print progress
        progress_bar = (
            f"Iteration {self.iteration}/{self.max_iterations} | "
            f"No improvement {self.no_improve}/{self.max_no_improve} | "
            f"Time {elapsed:.1f}/{self.time_limit:.1f}s"
        )
        print(progress_bar)  # Use carriage return to print on the same line

        # Check stopping conditions
        if self.iteration >= self.max_iterations:
            print("\nStopping: Max iterations reached.")
            return True
        if self.no_improve >= self.max_no_improve:
            print("\nStopping: Max no improvement reached.")
            return True

        return False
