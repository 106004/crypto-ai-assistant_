from flask import Blueprint, request

from line_bot import handle_webhook

webhook_bp = Blueprint("webhook", __name__)


@webhook_bp.route("/callback", methods=["POST"])
def callback():
    print("[Route] /callback webhook received")
    response = handle_webhook(request)
    print("[Route] webhook route complete")
    return response

