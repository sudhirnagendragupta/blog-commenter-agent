import json
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config.config import Config  # Import Config from config module
from core.scraper import WebScraper
from core.comment_generator import CommentGenerator


class CommentAgent:
    """Main agent class to orchestrate blog commenting."""

    def __init__(self):
        self.scraper = WebScraper()
        self.comment_generator = CommentGenerator()
        self.memory = self.load_memory()

    def load_memory(self):
        """Load memory of commented posts from JSON file."""
        try:
            with open(Config.MEMORY_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"commented_posts": []}
        except json.JSONDecodeError:
            print("Warning: Memory file is corrupted. Starting with empty memory.")
            return {"commented_posts": []}

    def save_memory(self):
        """Save memory of commented posts to JSON file."""
        with open(Config.MEMORY_FILE, 'w') as f:
            json.dump(self.memory, f, indent=4)

    def is_already_commented(self, post_url):
        """Check if the post URL is already in memory."""
        return post_url in self.memory["commented_posts"]

    def mark_post_as_commented(self, post_url):
        """Add the post URL to memory."""
        if not self.is_already_commented(post_url):
            self.memory["commented_posts"].append(post_url)
            self.save_memory()

    def post_comment_selenium(self, url, comment_text, headless=Config.SELENIUM_HEADLESS):
        """Posts a comment to Disqus using Selenium WebDriver."""
        # Configure Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--window-size=1920,1080")  # Set window size
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        # Add user agent to make it look like a real browser
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Initialize the driver
        service = Service(executable_path=Config.SELENIUM_CHROMEDRIVER_PATH)  # Use path from Config
        driver = webdriver.Chrome(service=service, options=chrome_options)  # Use service object

        try:
            # Navigate to the blog post
            print(f"Loaded page: {url}")
            driver.get(url)

            # Find and click the comments button to load Disqus
            try:
                # Wait for the page to load
                time.sleep(5)

                # Look for the Comments button - try different possible selectors
                comment_buttons = []
                try:
                    comment_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Comments')]")
                    if not comment_buttons:
                        comment_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), 'Comments')]")
                    if not comment_buttons:
                        comment_buttons = driver.find_elements(By.CSS_SELECTOR, ".comment-count, .comments-link, #comments-button")
                except Exception as e:  # Catch specific exceptions if you want to debug button finding more
                    print(f"Error finding comment button: {e}")
                    pass

                if comment_buttons:
                    print("Found 'Comments' button, clicking it...")
                    comment_buttons[0].click()
                    time.sleep(3)  # Wait for Disqus to load after clicking
                else:
                    print("No comments button found, assuming Disqus is already loaded...")

                # Wait for Disqus iframe to load - **Improved iframe detection**
                disqus_iframe = None
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        if "disqus" in iframe.get_attribute("src").lower():  # Lowercase for case-insensitive check
                            driver.switch_to.frame(iframe)
                            print(f"Switched to Disqus iframe: {iframe.get_attribute('src')}")
                            disqus_iframe = iframe  # Mark iframe as found
                            break  # Exit loop after finding the Disqus iframe
                    except:  # Handle potential errors getting iframe src
                        continue

                if not disqus_iframe:  # Check if iframe was actually found and switched to
                    print("❌ No Disqus iframe found or failed to switch. Checking for alternative Disqus elements (may not be in iframe).")
                    # Try to find any Disqus elements on the page if iframe approach fails as fallback.
                    disqus_elements = driver.find_elements(By.CSS_SELECTOR, "[id*='disqus']")
                    if disqus_elements:
                        print(f"Found alternative Disqus elements (not iframe), assuming Disqus is directly embedded.")
                        # Assuming Disqus is directly embedded, no need to switch frame.
                    else:
                        print("❌ No Disqus iframe or alternative elements found. Disqus might not be loaded or incorrectly detected.")
                        return False  # Early return if no Disqus context found

                # Try to find the start discussion by focusing on textarea
                try:
                    comment_textarea_element = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='textbox'][contenteditable='true']"))
                    )
                    print("Found comment textarea (editable div), clicking to focus...")
                    comment_textarea_element.click()  # Click to focus and start discussion
                    time.sleep(2)  # Wait for UI to update after focusing textarea
                except TimeoutException:
                    print("❌ Timed out waiting for comment textarea (editable div) to be clickable.")
                    return False

                # Now try to find the comment textarea - **Adjusted textarea selector to target the actual textarea element**
                try:
                    comment_textarea = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR,
                                                         "textarea#post-message, textarea.textarea, div[role='textbox'][contenteditable='true']"))
                    )  # Include editable div as fallback if textarea not directly found
                    print("✅ Found comment textarea element.")

                    # Enter the comment text
                    print("Entering comment text...")
                    driver.execute_script("arguments[0].scrollIntoView(true);", comment_textarea)
                    time.sleep(1)
                    driver.execute_script("arguments[0].focus();", comment_textarea)
                    comment_textarea.send_keys(comment_text)
                    time.sleep(1)

                    # **Guest Form Interaction START**

                    # 1. Click Name Field to expand form
                    try:
                        name_field_placeholder = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Name']"))
                        )
                        print("Found 'Name' field, clicking it...")
                        name_field_placeholder.click()
                        time.sleep(1)  # Small wait for form expansion
                    except TimeoutException:
                        print("❌ Timed out waiting for 'Name' field to be clickable.")
                        return False

                    # 2. Enter Guest Name
                    try:
                        name_field = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.NAME, "display_name"))  # Using display_name as seen in HTML
                        )
                        name_field.send_keys(Config.COMMENT_NAME)  # Use name from config
                        print(f"Entered guest name: {Config.COMMENT_NAME}")
                    except TimeoutException:
                        print("❌ Timed out waiting for name input field to be present.")
                        return False

                    # 3. Check 'Post as Guest' Checkbox
                    try:
                        guest_checkbox = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//input[@name='author-guest']"))
                        )
                        print("Found 'Post as a guest' checkbox, clicking it...")
                        guest_checkbox.click()
                        time.sleep(1)  # Small wait after checkbox click
                    except TimeoutException:
                        print("❌ Timed out waiting for 'Post as a guest' checkbox to be clickable.")
                        return False

                    # 4. Enter Guest Email
                    try:
                        email_field = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.NAME, "email"))
                        )
                        email_field.send_keys(Config.COMMENT_EMAIL)  # Use email from config
                        print(f"Entered guest email: {Config.COMMENT_EMAIL}")
                    except TimeoutException:
                        print("❌ Timed out waiting for email input field to be present.")
                        return False

                    print("✅ Guest form filled. Waiting for manual reCAPTCHA completion... PLEASE COMPLETE THE reCAPTCHA MANUALLY IN THE BROWSER!")
                    time.sleep(Config.MANUAL_CAPTCHA_TIMEOUT)  # **Wait for manual reCAPTCHA completion - Configurable Timeout**
                    print("⌛️ Assuming reCAPTCHA completed. Proceeding...")

                    # **Guest Form Interaction END**

                    # Look for the post/submit comment button - **Using more specific selector for arrow button**
                    post_buttons = []
                    try:
                        post_buttons = driver.find_elements(By.CSS_SELECTOR, "button.proceed__button.btn.submit")  # More specific CSS for arrow button
                        if not post_buttons:  # Fallback to previous selectors if specific arrow button not found
                            post_buttons = driver.find_elements(By.XPATH,
                                                                "//button[contains(text(), 'Post') or contains(text(), 'Submit') or contains(text(), 'Comment')] | //button[contains(., 'Add to the discussion')] | //button[@type='submit'] | //button[contains(., 'Reply')] | //button[contains(@aria-label, 'Post')] | //button[contains(@aria-label, 'Comment')] | //button[contains(@class, 'submit')] | //button[contains(@class, 'post-button')] | //button[contains(@class, 'reply-button')] | //button[contains(@class, 'proceed__button')]")

                            if not post_buttons:  # Fallback CSS selectors
                                post_buttons = driver.find_elements(By.CSS_SELECTOR,
                                                                    ".btn-primary, .submit, .post-button, [type='submit'], .reply-button, .proceed__button, button.submit-button, button.post-button")
                    except Exception as post_button_err:  # More specific exception handling
                        print(f"Error finding post button: {post_button_err}")
                        pass

                    if post_buttons:
                        post_button = post_buttons[0]  # Get the first post button element
                        print("Found post button (arrow), waiting for it to be clickable...")
                        try:  # Add explicit wait for clickability for the post button
                            WebDriverWait(driver, Config.SELENIUM_TIMEOUT).until(EC.element_to_be_clickable(post_button))  # Configurable timeout
                            print("Post button is clickable, scrolling into view...")  # Add log message
                            driver.execute_script("arguments[0].scrollIntoView(true);", post_button)  # Scroll into view *before* click
                            time.sleep(1)  # Short wait after scroll, might not be strictly necessary
                            print("Clicking post button (arrow)...")
                            post_button.click()
                            time.sleep(Config.SELENIUM_WAIT_AFTER_COMMENT)  # Configurable wait after post click
                            print(
                                f"✅ Successfully posted comment to: {url} (hopefully, check website to confirm after captcha!)")  # Updated success message
                            return True
                        except TimeoutException:
                            print("❌ Timed out waiting for post button (arrow) to become clickable, or element is still not interactable after waiting.")
                            return False
                    else:
                        print("❌ No post button (arrow) found after entering comment and guest details.")
                        return False

                except TimeoutException:
                    print("❌ Timed out waiting for comment textarea or guest form elements.")

                    

                    # Debug info - print the page structure - Keep debug info, potentially expand if needed, focus on form.
                    print("\nPage elements for debugging (around guest form - first 100 elements from form):")  # Increased to 100
                    form_element = driver.find_element(By.TAG_NAME, "form")  # Assuming form is still relevant context
                    elements = form_element.find_elements(By.XPATH, ".//*")  # Search within the form
                    print(f"Found {len(elements)} form elements. Printing first 100 around guest form:")  # Increased to 100
                    for i, element in enumerate(elements[:100]):  # Increased to 100
                        print(
                            f"{i + 1}: Tag: {element.tag_name}, Class: {element.get_attribute('class')}, ID: {element.get_attribute('id')}, Text: '{element.text[:50]}...'")  # Print tag, class, id, and partial text

                    # Print common Disqus elements - Keep common element checks.
                    print("\nLooking for Disqus-specific elements:")
                    for selector in [".post-list", "#disqus_thread", ".textarea", ".wysiwyg", ".comment-box"]:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            print(f"Found {selector}: {len(elements)} elements")

                    # Print buttons - Keep button printing.
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    print(f"Found {len(buttons)} buttons. Printing first 5:")
                    for i, button in enumerate(buttons[:5]):  # Print first 5 buttons
                        print(f"Button {i + 1}: '{button.text}'")

                    return False

            except TimeoutException as e:
                print(f"❌ Timed out waiting for comment interface (initial load): {e}")
                return False
            except Exception as e:
                print(f"❌ General error posting comment: {e}")
                import traceback  # For detailed error info
                traceback.print_exc()  # Print full traceback
                return False

        finally:
            # Close the driver
            driver.quit()

    def run_agent(self):
        """Main function to run the blog commenting agent."""
        print("Starting Blog Commenting Agent...")

        posts = self.scraper.get_blog_posts(self)  # Pass self (CommentAgent instance) to scraper
        if not posts:
            print("No new blog posts found to comment on (or all are already commented). Exiting.")  # Updated message
            return

        processed_count = 0
        for post in posts:
            if processed_count >= Config.MAX_POSTS_TO_PROCESS:
                print(f"Reached maximum posts to process ({Config.MAX_POSTS_TO_PROCESS}). Stopping.")
                break

            # Memory check is now done in get_blog_posts, no need to check here again
            print(f"\n--- Processing post: {post['title']} ---")
            comment_text = self.comment_generator.generate_comment(post)
            if comment_text:
                print(f"Generated comment: {comment_text[:80]}...")  # Preview

                time.sleep(Config.DELAY_BETWEEN_COMMENTS + random.uniform(0.5, 1.5))  # Delay before comment

                if self.post_comment_selenium(post['url'], comment_text, headless=Config.SELENIUM_HEADLESS):  # Use headless config
                    self.mark_post_as_commented(post['url'])
                    processed_count += 1
                    print(f"✅ Commented on: {post['url']}")
                else:
                    print(f"❌ Failed to post comment on: {post['url']}")
            else:
                print(f"❌ Could not generate comment for: {post['url']}")

        print("\nBlog Commenting Agent run finished.")
        print(f"Successfully commented on {processed_count} new posts.")