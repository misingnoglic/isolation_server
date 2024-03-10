import os

ANNOUNCEMENT_WEBHOOK_URL = os.environ.get('ANNOUNCEMENT_WEBHOOK_URL', '')
GAME_WEBHOOK_URL = os.environ.get('GAME_WEBHOOK_URL', '')
DISCORD_CHANNEL_ID = os.environ.get('DISCORD_CHANNEL_ID', '')
DB_URL = f"postgresql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
