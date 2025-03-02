import os

class Config:
    """Configuration class for the Blog Commenter Agent."""

    # Website configuration
    SITE_URL = "https://example.com"  # Your website URL (no trailing slash)
    BLOG_BASE_URL = f"{SITE_URL}/blog/"  # Blog section URL

    # Disqus configuration
    DISQUS_SHORTNAME = "your-disqus-shortname"  # Your Disqus forum shortname

    # OpenAI API configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Get API key from environment variable

    # Scraping and commenting configuration
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    DELAY_BETWEEN_REQUESTS = 2  # Delay in seconds between HTTP requests
    DELAY_BETWEEN_COMMENTS = 15  # Delay in seconds between posting comments
    MAX_POSTS_TO_PROCESS = 1  # Limit number of posts to process in one run

    # Comment user configuration
    COMMENT_NAME = "AI Assistant"
    COMMENT_EMAIL = "ai-assistant@example.com"  # Your actual email for Disqus

    # Memory configuration - make sure the 'memory' directory exists in the project root
    MEMORY_FILE = "memory/agent_memory.json"  # File to store memory of commented posts

    # Debug mode
    DEBUG = True  # Set to True for verbose logging

    # Selenium settings
    SELENIUM_HEADLESS = False  # Set to False to show browser UI for captcha solving
    SELENIUM_TIMEOUT = 30  # Default timeout in seconds
    SELENIUM_WAIT_AFTER_COMMENT = 10  # Seconds to wait after posting a comment
    SELENIUM_CHROMEDRIVER_PATH = '/opt/homebrew/bin/chromedriver' # Path to chromedriver
    # Manual captcha solving
    MANUAL_CAPTCHA_TIMEOUT = 10  # Maximum time (in seconds) to wait for manual captcha solving