import os

from flask import Flask, jsonify

from market_collector import collect_market_data  # compatibility for routes.cron wrapper
from routes.cron import cron_bp
from routes.health import health_bp
from routes.webhook import webhook_bp


app = Flask(__name__)
print("[App] Flask app initialized")

app.register_blueprint(cron_bp)
app.register_blueprint(health_bp)
app.register_blueprint(webhook_bp)
print("[App] Blueprints registered")


def _start_scheduler_once():
    """Compatibility helper for legacy tests and debug reloader behavior."""

    if os.environ.get("FLASK_DEBUG") == "1" and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return False

    import scheduler

    scheduler.start_scheduler()
    return True


@app.route("/")
def home():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
