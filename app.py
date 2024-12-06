from flask import Flask
from api.routes import app_routes
from config.settings import init_sentry
import threading
from services.conversation_service import cleanup_old_conversations

app = Flask(__name__)
app.register_blueprint(app_routes)

def init_app():
    init_sentry()
    cleanup_thread = threading.Thread(target=cleanup_old_conversations, daemon=True)
    cleanup_thread.start()
    return app

if __name__ == '__main__':
    app = init_app()
    app.run(host='0.0.0.0', port=5000)