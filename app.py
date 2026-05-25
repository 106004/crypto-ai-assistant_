from flask import Flask, jsonify

from routes.cron import cron_bp
from routes.health import health_bp
from routes.webhook import webhook_bp


app = Flask(__name__)
print("[App] Flask app initialized")

app.register_blueprint(cron_bp)
app.register_blueprint(health_bp)
app.register_blueprint(webhook_bp)
print("[App] Blueprints registered")


@app.route("/")
def home():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
