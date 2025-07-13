# VoiceForAll

VoiceForAll is a web-based complaint submission system designed to empower citizens to report issues anonymously, which are then posted to Twitter (X) for visibility after reaching a vote threshold. The system uses Flask for the backend, Gemini AI for complaint summarization, KeyBERT for hashtag generation, and a React-based frontend for user interaction. Complaints are tagged with relevant Twitter handles (e.g., `@Raise_Vote_Fix`, `@CMOf_Karnataka`) based on their category and location.

## Features

- **Anonymous Complaint Submission**: Users submit complaints with optional images (PNG, JPEG, GIF, max 16MB) and select a state in India.
- **AI-Powered Summarization**: Gemini AI generates a 4–5 word description, detects the Indian state (default: "India"), and assigns labels (e.g., "Women Safety", "Karnataka Issue").
- **Hashtag Generation**: KeyBERT generates 5–7 relevant hashtags for each complaint.
- **State Filtering**: Browse complaints by Indian state or view all complaints.
- **Voting System**: Complaints require 2 votes to be posted to Twitter, ensuring community validation.
- **Twitter Integration**: Posts complaints to Twitter with `@Raise_Vote_Fix` and a label-specific handle (e.g., `@CMOf_Karnataka` for Karnataka-related issues) when the vote threshold is reached. Supports the Twitter API free tier (100 posts/month).
- **Complaint Deletion**: Automatically deletes complaints and associated images after posting to Twitter.
- **Stats Dashboard**: Displays total complaints, votes, posted complaints, active complaints, and remaining Twitter posts.
- **Speech-to-Text**: Supports audio complaint submission with Google Cloud Speech-to-Text and translation to English.

## Project Structure

VoiceForAll/├── app.py                  # Flask backend with API endpoints├── twitter_agent.py        # Twitter API integration for posting complaints├── index.html              # React-based frontend (single-page application)├── .env                    # Environment variables (API keys)├── Uploads/                # Folder for storing uploaded images├── gcloud-key.json         # Google Cloud credentials for Speech-to-Text├── README.md               # Project documentation

## Prerequisites

- Python 3.8+
- Twitter Developer Account with API credentials (Bearer Token)
- Google Cloud Account with Speech-to-Text and Translate API enabled
- Gemini API key for complaint summarization
- Node.js (for React frontend, if extending `index.html`)

## Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/VoiceForAll.git
   cd VoiceForAll


Install Dependencies:
pip install flask flask-cors google-cloud-speech google-cloud-translate keybert werkzeug requests python-dotenv tweepy


Set Up Environment Variables:

Create a .env file in the root directory:TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_BEARER_TOKEN=your_bearer_token
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcloud-key.json


Replace your_api_key, your_api_secret, and your_bearer_token with credentials from the Twitter Developer Portal.
Replace your_gemini_api_key with your Gemini API key.
Ensure gcloud-key.json is a valid Google Cloud service account key with Speech-to-Text and Translate APIs enabled.


Create Uploads Folder:
mkdir Uploads


Ensure the folder has write permissions for storing images.


Run the Application:
python app.py


Access the app at http://127.0.0.1:5000.



Usage

Submit a Complaint:

Navigate to http://127.0.0.1:5000.
Enter a complaint (text or audio), select a state (e.g., "Karnataka"), and optionally upload images (max 2, PNG/JPEG/GIF).
The system uses Gemini AI to generate a 4–5 word description, detect the state, and assign labels (e.g., "Karnataka Issue" for Karnataka complaints).


Browse Complaints:

Filter complaints by state (e.g., "Karnataka" or "ALL").
View the 4–5 word description in complaint cards; expand to see full text, images, hashtags, and labels.


Vote on Complaints:

Click "Vote" on a complaint card (requires unique anonymous_id, use incognito mode for testing multiple votes).
After 2 votes, the complaint is posted to Twitter with @Raise_Vote_Fix and a label-specific handle (e.g., @CMOf_Karnataka), then deleted.


View Stats:

Check the stats tab for total complaints, votes, posted complaints, active complaints, and remaining Twitter posts (100/month limit).



Twitter Integration

Handles: Complaints are tagged with @Raise_Vote_Fix and a label-specific handle:
Women Safety: @Ministry_WCD
Corruption: @NHRCIndia
Infrastructure: @MinOfHUA_India
Health: @MinOfHFW_INDIA
Electricity: @MinistryOfEB
Public Safety: @HMO_India
Karnataka Issue: @CMOf_Karnataka
General: @PMof_India


Vote Threshold: Set to 2 votes in app.py (MockFirebaseUtils.vote_threshold).
API Limit: Tracks Twitter posts (100/month, free tier) via MockFirebaseUtils.twitter_posts.

Testing

Submit a Complaint:

Submit: "Poor street lighting in Bangalore" (state: Karnataka).
Verify: Description (e.g., "Streetlights need repair"), state ("Karnataka"), labels (e.g., "Karnataka Issue"), and 5–7 hashtags (e.g., #streetlights, #publicsafety).


Vote and Post:

Vote twice (use incognito mode to simulate different users).
Check Twitter (@Raise_Vote_Fix) for a post like: Streetlights need repair in Karnataka. #streetlights, #publicsafety @Raise_Vote_Fix @CMOf_Karnataka.
Confirm the complaint is deleted and images are removed from Uploads.


Stats:

Verify twitter_posts_remaining decreases in the stats tab.


Debugging:

Check Flask logs: tail -f app.log.
Ensure Twitter Bearer Token has write permissions.
Verify Gemini API and Google Cloud credentials are valid.



Deployment
To deploy on a server (e.g., Heroku, AWS, or Render):

Use a WSGI server like Gunicorn:pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app


Configure environment variables on the hosting platform.
Ensure the Uploads folder is writable.
Use a reverse proxy (e.g., Nginx) for production.
Monitor Twitter API usage to stay within the 100 posts/month limit.

Limitations

Twitter API Free Tier: Limited to 100 posts/month.
Audio Support: Requires Google Cloud Speech-to-Text and Translate APIs.
Mock Blockchain: Blockchain integration is mocked (MockBlockchainUtils); replace with a real blockchain for production.
Frontend: Single-page index.html (React-based); extend with additional pages if needed.

Contributing

Fork the repository.
Create a feature branch: git checkout -b feature-name.
Commit changes: git commit -m "Add feature".
Push to the branch: git push origin feature-name.
Open a pull request.

License
MIT License. See LICENSE for details.
Contact
For issues or suggestions, open a GitHub issue or contact the project maintainer.
Last updated: July 13, 2025```
