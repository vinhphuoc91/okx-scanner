# OKX Opportunity Scanner — Project Context

## Tổng quan
Real-time crypto opportunity scanner cho OKX. Chạy trên VPS Ubuntu, deploy qua git push.
- **Backend**: Python 3.10+, FastAPI, PostgreSQL, Redis, SQLAlchemy
- **Frontend**: TypeScript/React (thư mục `dashboard/`)
- **VPS**: `root@146.196.64.116`, thư mục `~/okx-scanner`

## Cấu trúc quan trọng
```
src/
  worker/
    main.py                   # Entry point worker chính
    scanner_loop.py           # Vòng lặp scan chính
    trade_tracker.py          # Tạo/confirm/đóng paper trade — FILE QUAN TRỌNG NHẤT
    pending_confirmations.py  # Redis store cho signals chờ confirm M15
    scheduler.py              # Điều phối tier scan interval
  strategy/                   # 8 strategies: funding, momentum, breakout, volume_anomaly,
                              #   trend_pullback, correlation_divergence, liquidation_zone, stat_arb
  db/
    models.py                 # ORM models — StrategySettings, PaperTrade, Opportunity
    repositories/
      strategy_settings.py   # DEFAULT_STRATEGY_SETTINGS dict — seed mặc định vào DB
      paper_trade.py          # CRUD paper trade + stats
  api/routes/
    alerts.py                 # /alerts, /alerts/stats, /alerts/confirm-failed
    strategy_settings.py      # CRUD settings qua API
config/
  settings.py                 # Pydantic settings từ .env
dashboard/                    # React frontend
scripts/
  seed_instruments.py         # Seed instruments từ OKX API
```

## Workflow deploy
```bash
# Local (Windows PowerShell)
git add .
git commit -m "message"
git push

# VPS
ssh root@146.196.64.116
cd ~/okx-scanner
git pull
docker compose restart worker   # hoặc: sudo systemctl restart okx-scanner
```

## Môi trường local vs VPS
- **Local**: Windows, PowerShell, dùng để develop
- **VPS**: Ubuntu, chạy production với Docker Compose
- **Không có venv đầy đủ trên local** — chỉ edit code, không chạy Python local
- Sau mỗi thay đổi: git push → VPS git pull → restart service

## Database
- PostgreSQL chạy trong Docker trên VPS
- Migrations: Alembic (`alembic upgrade head`)
- Reset strategy settings về default: gọi `repo.reset_to_defaults()` qua script

## Redis
- Dùng để lưu pending confirmations (TTL-based)
- Key prefix: `pending_confirm:{opportunity_id}`
- Index key: `pending_confirm:index`

## Logic confirm M15 (trade_tracker.py — _evaluate_pending)
Signal phát ra → chờ confirm qua 3 điều kiện trên candle M15:
1. `price_ok` — giá đi đúng hướng so với signal price
2. `rsi_ok` — RSI xác nhận momentum
3. `vol_ok` — volume đủ mạnh
Hiện tại: cần 2/3 điều kiện (đã fix từ 3/3), timeout 30 phút, cần 14 candles M15.

## Strategy Settings (DB table: strategy_settings)
Mỗi strategy có:
- `requires_confirmation`: có cần chờ M15 không
- `confirmation_candles`: số candles tối thiểu (default 2 cho strategies có confirmation)
- `max_concurrent`: số trade đồng thời tối đa
- `cooldown_hours`: thời gian chờ giữa 2 trade cùng symbol/strategy
- `min_score`: ngưỡng score tối thiểu để tạo trade
Strategies **có** confirmation: MOMENTUM, BREAKOUT, TREND_PULLBACK, LIQUIDATION_ZONE
Strategies **không** cần: FUNDING, VOLUME_ANOMALY, CORRELATION_DIVERGENCE, STAT_ARBITRAGE

## Các vấn đề đã biết / đang theo dõi
- Confirm Failed rate cao (đang fix) — nguyên nhân: điều kiện quá khắt khe, timeout ngắn
- Win rate thấp — cần thêm data để đánh giá
- Dependencies trên VPS: cài qua `pip install -e ".[dev]"` trong tmux để tránh disconnect

## Khi debug vấn đề confirm
1. Check log: `docker compose logs worker --tail=100 | grep confirm`
2. Check Redis: `redis-cli smembers pending_confirm:index`
3. Check DB: query `opportunities` table where `status = 'CONFIRM_FAILED'`

## Style & conventions
- Python: type hints đầy đủ, structlog cho logging, Pydantic v2
- Log format: `log.info("event.name", key=value)` — snake_case với dấu chấm
- Decimal cho giá (không dùng float)
- Tất cả datetime phải có timezone UTC