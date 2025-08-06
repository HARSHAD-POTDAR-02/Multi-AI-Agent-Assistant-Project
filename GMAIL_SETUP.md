# Gmail API Setup Guide

To enable email drafting functionality, you need to set up Gmail API credentials:

## Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Gmail API for your project

## Step 2: Create Credentials
1. Go to "Credentials" in the left sidebar
2. Click "Create Credentials" → "OAuth client ID"
3. Choose "Desktop application"
4. Download the JSON file and rename it to `credentials.json`
5. Place `credentials.json` in the project root directory

## Step 3: Set up GROQ API Key
1. Get your GROQ API key from [https://console.groq.com/](https://console.groq.com/)
2. Update the `.env` file with your actual API key:
   ```
   GROQ_API_KEY=your_actual_groq_api_key_here
   ```

## Step 4: First Run
- When you first use the email drafting feature, it will open a browser for Gmail authorization
- Grant the necessary permissions
- A `token.json` file will be created automatically

## Usage Examples
- "Draft an email to john@example.com about the meeting tomorrow"
- "Write an email to my boss about project update"
- "Compose an email thanking the client for their business"