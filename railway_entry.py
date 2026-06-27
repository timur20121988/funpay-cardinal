"""
Railway deployment entry point for FunPayCardinal.
Generates configs from environment variables, starts healthcheck server and the bot.
"""
import os
import sys
import time
import logging
import threading
import atexit

# ─── Healthcheck HTTP server (required by Railway) ────────────────────────────
from http.server import HTTPServer, BaseHTTPRequestHandler


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"FunPayCardinal is running")

    def log_message(self, *a):
        pass  # suppress HTTP server logs


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    atexit.register(server.shutdown)
    logging.getLogger("FPC-Railway").info(f"Healthcheck server started on port {port}")
    server.serve_forever()


# ─── Config generator from environment variables ─────────────────────────────
from configparser import ConfigParser
from Utils.cardinal_tools import hash_password


def generate_main_config() -> str:
    """
    Generate _main.cfg content from environment variables.
    Falls back to defaults for optional values.
    """
    sections = {
        "FunPay": {
            "golden_key": os.environ.get("GOLDEN_KEY", ""),
            "user_agent": os.environ.get(
                "FPC_USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/109.0.0.0 Safari/537.36"
            ),
            "autoRaise": os.environ.get("FPC_AUTO_RAISE", "0"),
            "autoResponse": os.environ.get("FPC_AUTO_RESPONSE", "0"),
            "autoDelivery": os.environ.get("FPC_AUTO_DELIVERY", "0"),
            "multiDelivery": os.environ.get("FPC_MULTI_DELIVERY", "0"),
            "autoRestore": os.environ.get("FPC_AUTO_RESTORE", "0"),
            "autoDisable": os.environ.get("FPC_AUTO_DISABLE", "0"),
            "oldMsgGetMode": os.environ.get("FPC_OLD_MSG_MODE", "0"),
            "keepSentMessagesUnread": os.environ.get("FPC_KEEP_UNREAD", "0"),
            "locale": os.environ.get("FPC_LOCALE", "ru"),
        },
        "Telegram": {
            "enabled": "1" if os.environ.get("TELEGRAM_TOKEN") else "0",
            "token": os.environ.get("TELEGRAM_TOKEN", ""),
            "secretKeyHash": hash_password(
                os.environ.get("TELEGRAM_SECRET_KEY", "default_secret_key")
            ),
            "proxy": os.environ.get("TELEGRAM_PROXY", ""),
            "blockLogin": os.environ.get("FPC_BLOCK_LOGIN", "0"),
        },
        "BlockList": {
            "blockDelivery": os.environ.get("FPC_BLOCK_DELIVERY", "0"),
            "blockResponse": os.environ.get("FPC_BLOCK_RESPONSE", "0"),
            "blockNewMessageNotification": os.environ.get("FPC_BLOCK_MSG_NOTIFY", "0"),
            "blockNewOrderNotification": os.environ.get("FPC_BLOCK_ORDER_NOTIFY", "0"),
            "blockCommandNotification": os.environ.get("FPC_BLOCK_CMD_NOTIFY", "0"),
        },
        "NewMessageView": {
            "includeMyMessages": os.environ.get("FPC_INCLUDE_MY_MSGS", "1"),
            "includeFPMessages": os.environ.get("FPC_INCLUDE_FP_MSGS", "1"),
            "includeBotMessages": os.environ.get("FPC_INCLUDE_BOT_MSGS", "0"),
            "notifyOnlyMyMessages": os.environ.get("FPC_NOTIFY_ONLY_MY", "0"),
            "notifyOnlyFPMessages": os.environ.get("FPC_NOTIFY_ONLY_FP", "0"),
            "notifyOnlyBotMessages": os.environ.get("FPC_NOTIFY_ONLY_BOT", "0"),
            "showImageName": os.environ.get("FPC_SHOW_IMAGE_NAME", "1"),
        },
        "Greetings": {
            "ignoreSystemMessages": os.environ.get("FPC_IGNORE_SYSTEM", "0"),
            "onlyNewChats": os.environ.get("FPC_ONLY_NEW_CHATS", "0"),
            "sendGreetings": os.environ.get("FPC_SEND_GREETINGS", "0"),
            "greetingsText": os.environ.get("FPC_GREETINGS_TEXT", "Привет, $chat_name!"),
            "greetingsCooldown": os.environ.get("FPC_GREETINGS_COOLDOWN", "2"),
        },
        "OrderConfirm": {
            "watermark": os.environ.get("FPC_WATERMARK_ORDER", "1"),
            "sendReply": os.environ.get("FPC_SEND_ORDER_REPLY", "0"),
            "replyText": os.environ.get(
                "FPC_ORDER_REPLY",
                "$username, спасибо за подтверждение заказа $order_id!\n"
                "Если не сложно, оставь, пожалуйста, отзыв!"
            ),
        },
        "ReviewReply": {
            "star1Reply": os.environ.get("FPC_STAR1_REPLY", "0"),
            "star2Reply": os.environ.get("FPC_STAR2_REPLY", "0"),
            "star3Reply": os.environ.get("FPC_STAR3_REPLY", "0"),
            "star4Reply": os.environ.get("FPC_STAR4_REPLY", "0"),
            "star5Reply": os.environ.get("FPC_STAR5_REPLY", "0"),
            "star1ReplyText": os.environ.get("FPC_STAR1_TEXT", ""),
            "star2ReplyText": os.environ.get("FPC_STAR2_TEXT", ""),
            "star3ReplyText": os.environ.get("FPC_STAR3_TEXT", ""),
            "star4ReplyText": os.environ.get("FPC_STAR4_TEXT", ""),
            "star5ReplyText": os.environ.get("FPC_STAR5_TEXT", ""),
        },
        "Proxy": {
            "enable": os.environ.get("FPC_PROXY_ENABLE", "0"),
            "proxy": os.environ.get("FPC_PROXY", ""),
            "check": os.environ.get("FPC_PROXY_CHECK", "0"),
        },
        "Other": {
            "watermark": os.environ.get("FPC_WATERMARK", "🐦"),
            "requestsDelay": os.environ.get("FPC_REQUESTS_DELAY", "4"),
            "language": os.environ.get("FPC_LANGUAGE", "ru"),
        },
    }

    config = ConfigParser(delimiters=(":",), interpolation=None)
    config.optionxform = str

    for section, params in sections.items():
        config.add_section(section)
        for key, value in params.items():
            config.set(section, key, str(value))

    # Write to file with correct formatting
    output_lines = []
    for section in config.sections():
        output_lines.append(f"[{section}]")
        for key, value in config.items(section):
            output_lines.append(f"{key} : {value}")
        output_lines.append("")

    return "\n".join(output_lines)


def ensure_directories():
    """Create required directories."""
    dirs = ["configs", "logs", "storage", "storage/cache",
            "storage/plugins", "storage/products", "plugins"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def ensure_config_files():
    """Create config files from env vars."""
    # _main.cfg
    main_cfg_content = generate_main_config()
    with open("configs/_main.cfg", "w", encoding="utf-8") as f:
        f.write(main_cfg_content)

    # auto_delivery.cfg (empty)
    if not os.path.exists("configs/auto_delivery.cfg"):
        with open("configs/auto_delivery.cfg", "w", encoding="utf-8") as f:
            pass

    # auto_response.cfg (empty or from env var)
    if not os.path.exists("configs/auto_response.cfg"):
        with open("configs/auto_response.cfg", "w", encoding="utf-8") as f:
            auto_response = os.environ.get("FPC_AUTO_RESPONSE_CONFIG", "")
            if auto_response:
                f.write(auto_response)


def run_bot():
    """Start the actual FunPayCardinal bot by running main.py in its own context."""
    try:
        # Change to script directory (main.py does this too)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(base_dir)

        ensure_directories()
        ensure_config_files()

        # Execute main.py as __main__ (it's a script, not an importable module)
        import runpy
        runpy.run_path(os.path.join(base_dir, "main.py"), run_name="__main__")
    except Exception as e:
        logger = logging.getLogger("FPC-Railway")
        logger.critical(f"Bot crashed on startup: {e}", exc_info=True)
        sys.exit(1)


# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Setup basic logging first
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logger = logging.getLogger("FPC-Railway")

    logger.info("Starting FunPayCardinal on Railway...")
    logger.info(f"Python version: {sys.version}")

    # Check required env vars
    if not os.environ.get("GOLDEN_KEY"):
        logger.warning("GOLDEN_KEY is not set! The bot may not work correctly.")

    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.warning(
            "TELEGRAM_TOKEN is not set! Telegram control will be disabled."
        )

    # Start healthcheck server in a background thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info("Healthcheck server is running...")

    # Small delay to let Railway healthcheck pass before bot starts
    time.sleep(1)

    # Run the bot (blocking — it runs its own event loop)
    run_bot()
