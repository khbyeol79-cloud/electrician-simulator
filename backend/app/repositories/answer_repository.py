from __future__ import annotations

from app.domain import AnswerDefinition

from .problem_repository import ProblemRepository


class AnswerRepository:
    """Internal-only answer access. Never use this object as an API response."""

    def __init__(self, problem_repository: ProblemRepository):
        self._problem_repository = problem_repository

    def get_internal(self, problem_id: str) -> AnswerDefinition | None:
        package = self._problem_repository._get_package_internal(problem_id)
        return package.answer if package else None

