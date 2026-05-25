from apscheduler.schedulers.background import BackgroundScheduler

from data.repositories.market_data_repository import get_market_data_by_symbol
from data.repositories.user_repository import get_all_users
from line_bot import push_message
from market_collector import collect_market_data
from services.jobs.scheduler_service import (
    run_daily_guide_job,
    run_favorite_coin_job,
    run_market_update_job,
)
from services.line.message_service import (
    format_daily_guide_message,
    format_missing_favorite_coin_message,
    format_price_message,
)
from services.market.freshness_service import is_market_data_fresh
from utils.logger import log_info


_scheduler = None

# Render 免費版會 sleep，因此正式排程改由 external cron 觸發。
# 這個模組只保留作為本機開發時的手動備用排程入口。


def send_daily_manual_to_all_users():
    return run_daily_guide_job(
        get_users_fn=get_all_users,
        push_message_fn=push_message,
        guide_message_fn=format_daily_guide_message,
    )


def send_hourly_favorite_coin_price():
    return run_favorite_coin_job(
        get_users_fn=get_all_users,
        get_market_data_by_symbol_fn=get_market_data_by_symbol,
        push_message_fn=push_message,
        is_market_data_fresh_fn=is_market_data_fresh,
        price_message_fn=format_price_message,
        missing_favorite_coin_message_fn=format_missing_favorite_coin_message,
    )


def update_market_data_job():
    return run_market_update_job(collector=collect_market_data)


def test_daily_manual():
    send_daily_manual_to_all_users()


def test_hourly_favorite_coin_price():
    send_hourly_favorite_coin_price()


def start_scheduler():
    global _scheduler

    if _scheduler and _scheduler.running:
        log_info("Scheduler", "scheduler already running")
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="Asia/Taipei")
    _scheduler.add_job(
        send_daily_manual_to_all_users,
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_manual_9am",
        replace_existing=True,
    )
    _scheduler.add_job(
        send_hourly_favorite_coin_price,
        trigger="interval",
        hours=1,
        id="hourly_favorite_coin_price",
        replace_existing=True,
    )
    _scheduler.add_job(
        update_market_data_job,
        trigger="interval",
        minutes=5,
        id="market_data_update_5min",
        replace_existing=True,
    )

    _scheduler.start()
    log_info(
        "Scheduler",
        "scheduler started: daily guide at 9:00, hourly favorite coin push, market update every 5 minutes",
    )
    return _scheduler


if __name__ == "__main__":
    start_scheduler()
