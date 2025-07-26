import os

USER_ID = os.getenv("USER", "default_user")
DEFAULT_APP_ID = "openmemory"

# Maximum allowed page size for paginated memory responses
# Defaults to 100 which aligns with API contract tests
MAX_MEMORY_PAGE_SIZE = int(os.getenv("MAX_MEMORY_PAGE_SIZE", "100"))
