import os
from pathlib import Path
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration

load_dotenv()

CLEANUP_INTERVAL = 600
MAX_CONVERSATION_LENGTH = 50
DATA_DIRECTORY = Path("doctorsData")
CACHE_FILE = DATA_DIRECTORY / "cache_index.json"
CACHE_REFRESH_INTERVAL = 3600

DATA_DIRECTORY.mkdir(exist_ok=True)

def init_sentry():
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[
            FlaskIntegration(),
            ThreadingIntegration(propagate_hub=True)
        ],
        environment=os.getenv('ENVIRONMENT', 'development'),
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        enable_tracing=True,
        debug=True
    )
    
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("service", "doctor-chat-service")