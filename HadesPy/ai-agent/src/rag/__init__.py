"""RAG module for course recommendations."""

from src.rag.course_recommender import (
    CourseRecommender,
    CourseRecommendation,
    StudentPreferences,
)

__all__ = [
    "CourseRecommender",
    "CourseRecommendation",
    "StudentPreferences",
]
