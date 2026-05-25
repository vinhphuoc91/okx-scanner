"""Strategy settings API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.repositories.strategy_settings import StrategySettingsRepository
from src.db.session import get_db
from src.schemas.strategy_settings import GlobalSettingsUpdate, StrategySettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/strategies")
def list_strategy_settings(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return all strategy risk profiles and global config."""
    repo = StrategySettingsRepository(db)
    settings = repo.get_all_settings()
    global_cfg = repo.get_global_config()
    return {
        "strategies": [repo.to_dict(row) for row in settings.values()],
        "global": repo.global_to_dict(global_cfg),
    }


@router.put("/strategies/{strategy_type}")
def update_strategy_settings(
    strategy_type: str,
    payload: StrategySettingsUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update one strategy's risk profile."""
    repo = StrategySettingsRepository(db)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    try:
        row = repo.update_settings(strategy_type, **updates)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown strategy: {strategy_type}",
        ) from None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    db.commit()
    return repo.to_dict(row)


@router.post("/strategies/reset")
def reset_strategy_settings(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Reset all strategies and global config to defaults."""
    repo = StrategySettingsRepository(db)
    repo.reset_to_defaults()
    db.commit()
    settings = repo.get_all_settings()
    return {
        "strategies": [repo.to_dict(row) for row in settings.values()],
        "global": repo.global_to_dict(repo.get_global_config()),
    }


@router.put("/global")
def update_global_settings(
    payload: GlobalSettingsUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update global scanner settings."""
    repo = StrategySettingsRepository(db)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    row = repo.update_global_config(**updates)
    db.commit()
    return repo.global_to_dict(row)
