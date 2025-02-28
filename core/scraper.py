import requests
import time
import random
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from config.config import Config # Import Config from config module

class WebScraper:
    """Web scraper class to discover blog posts."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": Config.USER_AGENT})

    def test_connection(self):
        """Test if we can access the website"""
        try:
            print(f"Testing connection to {Config.SITE_URL}...")
            response = self.session.get(Config.SITE_URL)
            if response.status_code == 200:
                print(f"✅ Successfully connected to {Config.SITE_URL}")
                return True
            else:
                print(f"❌ Failed to connect to {Config.SITE_URL}: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Exception when connecting to {Config.SITE_URL}: {e}")
            return False

    def get_page(self, url):
        """Get page content with proper rate limiting"""
        time.sleep(Config.DELAY_BETWEEN_REQUESTS + random.uniform(0.5, 1.5))  # Random delay
        try:
            response = self.session.get(url)
            response.raise_for_status()
            if Config.DEBUG:
                print(f"Retrieved page: {url} ({len(response.text)} bytes)")
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_post_links_from_page(self, html, page_url):
        """Extract blog post links from an HTML page"""
        if not html:
            return []

        post_links = []
        soup = BeautifulSoup(html, 'html.parser')

        # Check for articles in the current page
        # This handles the structure in both blog page and tag pages
        articles = soup.find_all('article', class_='article') or soup.find_all('div', class_='article')

        if Config.DEBUG:
            print(f"Found {len(articles)} article elements on the page {page_url}")

        for article in articles:
            # Try to find the title link using various possible structures
            title_link = None

            # Structure 1: Find h2 with article__title class that contains an anchor
            title_elem = article.find(['h2', 'h3'], class_='article__title')
            if title_elem:
                title_link = title_elem.find('a', href=True)

            # Structure 2: Alternative direct approach
            if not title_link:
                title_link = article.find('a', href=True)

            if title_link and 'href' in title_link.attrs:
                # Ensure it's an absolute URL
                post_url = title_link['href']
                if not post_url.startswith('http'):
                    post_url = urljoin(Config.SITE_URL, post_url)

                post_links.append(post_url)
                if Config.DEBUG:
                    print(f"Found post link: {post_url}")

        return post_links

    def get_pagination_links(self, html, base_url):
        """Extract pagination links from the blog index page"""
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        page_links = []

        # Look for pagination div
        pagination = soup.find('div', class_='pagination')
        if pagination:
            # Find all links that match the page pattern
            for a_tag in pagination.find_all('a', href=True):
                href = a_tag['href']
                if '/blog/page' in href:
                    full_url = urljoin(base_url, href)
                    page_links.append(full_url)
                    if Config.DEBUG:
                        print(f"Found pagination link: {full_url}")

        return page_links

    def get_blog_posts(self, comment_agent): # Pass comment_agent instance here
        """Discover blog posts by crawling the site, checking memory."""
        if not self.test_connection():
            return []

        posts = []
        all_post_links = set()  # Use a set to avoid duplicates

        # Start with the blog index page
        print(f"Starting blog post discovery at {Config.BLOG_BASE_URL}")
        html = self.get_page(Config.BLOG_BASE_URL)
        if not html:
            print("Could not retrieve the blog index page. Check URL and connection.")
            return posts

        # Get post links from the main blog page
        blog_post_links = self.extract_post_links_from_page(html, Config.BLOG_BASE_URL)
        for link in blog_post_links:
            all_post_links.add(link)

        # Get pagination links and process them
        pagination_links = self.get_pagination_links(html, Config.BLOG_BASE_URL)
        for page_link in pagination_links[:3]:  # Limit to first 3 pages
            page_html = self.get_page(page_link)
            page_post_links = self.extract_post_links_from_page(page_html, page_link)
            for link in page_post_links:
                all_post_links.add(link)

        # Also check tags page for additional posts
        tags_url = f"{Config.SITE_URL}/tags/"
        tags_html = self.get_page(tags_url)
        tags_post_links = self.extract_post_links_from_page(tags_html, tags_url)
        for link in tags_post_links:
            all_post_links.add(link)

        # Limit the number of posts to process
        all_post_links = list(all_post_links)[:Config.MAX_POSTS_TO_PROCESS]

        print(f"Discovered {len(all_post_links)} unique blog post links (before memory check)") # Updated log

        # Process each post link to check for Disqus capability and memory
        for full_url in list(all_post_links): # Iterate over a *copy* to allow removal
            if comment_agent.is_already_commented(full_url): # Check memory *first*
                print(f"Skipping already commented post (from memory): {full_url}")
                all_post_links.remove(full_url) # Remove from set if already commented
                continue # Skip to next post

            post_html = self.get_page(full_url)

            if post_html:
                post_soup = BeautifulSoup(post_html, 'html.parser')

                # Extract post information
                title_elem = post_soup.find('h1', class_='post-title')
                title = title_elem.text.strip() if title_elem else "Unknown Title"

                # Get the post content
                content_elem = post_soup.find('div', class_='post__content')
                content = content_elem.text.strip() if content_elem else ""

                # Check if this post has Disqus capability (even if not loaded)
                # Look for either the disqus thread container or the button to load comments
                has_disqus_container = bool(post_soup.find('div', id='disqus_thread'))
                has_disqus_button = bool(post_soup.find('button', id='show-comments-button'))
                has_disqus_script = bool(post_soup.find(lambda tag: tag.name == 'script' and
                                                          tag.string and
                                                          'disqus' in tag.string))

                # Check if post has Disqus capability (any of the above)
                has_disqus = has_disqus_container or has_disqus_button or has_disqus_script

                if has_disqus and content:
                    # Extract post slug for Disqus from URL
                    parsed_url = urlparse(full_url)
                    post_slug = parsed_url.path.split('/')[-1]
                    if post_slug.endswith('.html'):
                        post_slug = post_slug[:-5]  # Remove .html if present

                    post = {
                        'url': full_url,
                        'title': title,
                        'content': content,
                        'slug': post_slug
                    }
                    posts.append(post)
                    print(f"Found commentable post: {title}")
                else:
                    if Config.DEBUG:
                        reason = "missing content" if not content else "no Disqus components found"
                        print(f"Skipping post '{title}': {reason}")
                        print(f"  - Disqus container: {has_disqus_container}")
                        print(f"  - Disqus button: {has_disqus_button}")
                        print(f"  - Disqus script: {has_disqus_script}")

        print(f"Found {len(posts)} blog posts that can receive new comments (after memory check)") # Updated log
        return posts