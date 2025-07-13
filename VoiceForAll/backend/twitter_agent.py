
import tweepy
from dotenv import load_dotenv
import os

load_dotenv()

class TwitterAgent:
    def __init__(self, label_to_twitter):
        self.label_to_twitter = label_to_twitter  # Store the mapping
        try:
            self.client = tweepy.Client(
                bearer_token=os.getenv('TWITTER_BEARER_TOKEN')
            )
        except Exception as e:
            raise Exception(f"Failed to initialize Twitter client: {str(e)}")

    def post_complaint(self, complaint):
        try:
            # Construct tweet with description, state, hashtags, and Twitter handles
            twitter_handle = self.label_to_twitter.get(complaint['labels'][0], '@Yuvi564321')
            message = f"{complaint['description']} in {complaint['state']}. {', '.join(complaint['hashtags'])} @Yuvi564321 {twitter_handle}"
            # Ensure message is within Twitter's 280-character limit
            if len(message) > 280:
                message = message[:277] + "..."
            self.client.create_tweet(text=message)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
