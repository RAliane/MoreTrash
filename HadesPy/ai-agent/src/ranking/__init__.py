"""Ranking module for course recommendation reranking using XGBoost.

This module provides learning-to-rank capabilities for optimizing
course recommendation ordering based on learned preferences.
"""

from src.ranking.xgboost_ranker import CourseRanker
from src.ranking.config import RankingConfig, get_ranking_config

__all__ = ["CourseRanker", "RankingConfig", "get_ranking_config"]
