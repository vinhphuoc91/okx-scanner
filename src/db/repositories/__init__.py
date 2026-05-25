"""Database repositories."""

from src.db.repositories.instrument import InstrumentRepository
from src.db.repositories.opportunity import OpportunityRepository
from src.db.repositories.paper_trade import PaperTradeRepository
from src.db.repositories.score import ScoreRepository
from src.db.repositories.strategy_settings import StrategySettingsRepository

__all__ = [
    "InstrumentRepository",
    "OpportunityRepository",
    "PaperTradeRepository",
    "ScoreRepository",
    "StrategySettingsRepository",
]
