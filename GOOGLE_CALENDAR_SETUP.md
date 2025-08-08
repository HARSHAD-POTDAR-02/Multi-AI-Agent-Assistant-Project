# Google Calendar & Meet Integration Setup

## Step 1: Google Cloud Console Setup

### 1.1 Create/Select Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Create a new project or select existing one
4. Note your project name

### 1.2 Enable Calendar API
1. In the left sidebar, click **"APIs & Services"** → **"Library"**
2. Search for **"Google Calendar API"**
3. Click on it and press **"ENABLE"**
4. Wait for activation (may take 1-2 minutes)

### 1.3 Create OAuth Credentials
1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. If prompted, configure OAuth consent screen:
   - Choose **"External"** user type
   - Fill required fields:
     - App name: `Simi.ai Calendar`
     - User support email: your email
     - Developer contact: your email
   - Click **"SAVE AND CONTINUE"** through all steps
4. Back to credentials, select **"Desktop application"**
5. Name it: `Simi.ai Calendar Client`
6. Click **"CREATE"**

### 1.4 Download Credentials
1. Click the **download icon** next to your new credential
2. Save the file as `calendar_credentials.json`
3. Move it to: `Multi-AI-Agent-Assistant-Project/src/calendar_credentials.json`

## Step 2: Install Dependencies

Open terminal in project root and run:
```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

## Step 3: Test Setup

### 3.1 First Run (OAuth Setup)
1. Start the backend: `python backend.py`
2. Try: "Schedule a meeting tomorrow at 2 PM"
3. A browser window will open for Google OAuth
4. Sign in and grant calendar permissions
5. The `calendar_token.json` file will be created automatically

### 3.2 Verify Integration
- Check if `src/calendar_token.json` exists
- Try scheduling another meeting
- Check your Google Calendar for the created event
- Verify the Google Meet link works

## Step 4: Usage Examples

Once setup is complete, you can use natural language:

```
"Schedule a meeting with John tomorrow at 2 PM"
"Set up a team call for Friday 10 AM for 30 minutes" 
"Create a meeting called 'Project Review' next Monday"
"Schedule a 1-hour meeting with sarah@company.com at 3 PM today"
```

## Troubleshooting

### Error: "Calendar setup needed"
- Ensure `calendar_credentials.json` is in `/src/` folder
- Check file permissions

### Error: "Access denied"
- Re-run OAuth flow by deleting `calendar_token.json`
- Ensure Calendar API is enabled in Google Cloud Console

### No Meet link generated
- Ensure Google Meet is enabled in your Google Workspace
- Check if your Google account has Meet access

### Meeting not appearing in calendar
- Check timezone settings
- Verify calendar permissions in OAuth consent

## File Structure
```
src/
├── calendar_credentials.json  (you create this)
├── calendar_token.json       (auto-generated)
├── google_calendar_service.py (already created)
└── agents/
    └── calendar_orchestrator.py (updated)
```

## Security Notes
- Never commit `calendar_credentials.json` or `calendar_token.json` to version control
- These files contain sensitive authentication data
- Keep them secure and private