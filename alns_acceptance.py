from typing import Any


class CustomContainerAcceptance:
    """
    Custom acceptance criterion that mimics the original acceptance_criteria function.
    Accept if all containers are at least FEASIBLE and aggregate score improves,
    or with a 5% random chance.
    """

    def __call__(self, rng: Any, best: Any, current: Any, candidate: Any) -> bool:
        """
        ALNS acceptance criterion interface.

        Args:
            rng: Random number generator
            best: Best state found so far
            current: Current state
            candidate: Candidate state to evaluate

        Returns:
            bool: True if candidate should be accepted
        """
        import random

        # Check if candidate is feasible
        if not candidate.is_feasible():
            return False

        candidate_score = candidate.objective()
        best_score = best.objective()

        print(f'New solution aggregate score: {candidate_score}, current best score: {best_score}')

        # Accept if better or with 5% random chance
        accept = candidate_score < best_score or random.random() < 0.05

        # Print in green if True, red if False
        color = '\033[92m' if accept else '\033[91m'
        print(f'{color}Acceptance return value: {accept}\033[0m')

        return accept
