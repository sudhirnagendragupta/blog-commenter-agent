from openai import OpenAI
from config.config import Config # Import Config from config module

class CommentGenerator:
    """Comment generator class using OpenAI's GPT models."""

    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)  # Use the new client

    def generate_comment(self, post):
        """Generate a thoughtful comment based on the blog post content using GPT-4o"""
        system_message = """You are an intelligent blog reader who writes thoughtful comments.
Your comments should be insightful, relevant to the post content, and add value to the discussion.
Your tone should be friendly, curious, and enthusiastic about the topic.
Always reference specific details from the blog post to show you've read it carefully."""

        user_message = f"""I'm going to show you a blog post. Please write a thoughtful, engaging comment that adds value to the discussion.
The comment should be insightful, reference specific parts of the post, and possibly ask a thoughtful question or add additional context.
Keep the comment between 3-5 sentences, friendly and conversational in tone.

Blog Post Title: {post['title']}
Blog Post Content:
{post['content'][:4000]}  # Truncate if too long

Generate a thoughtful comment for this blog post:"""

        try:
            print(f"Generating comment for post: {post['title']}")

            # Correct API Call using the new OpenAI Client
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Ensure correct model usage
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150,
                temperature=0.7
            )

            comment = response.choices[0].message.content.strip()  # Corrected response parsing
            print(f"Comment generated successfully ({len(comment)} chars)")
            return comment

        except Exception as e:
            print(f"Error generating comment: {e}")
            return "I found this post very insightful and well-written. Thanks for sharing your expertise on this topic!"