# Simi.ai - Multi-AI Agent Assistant

A modern React-based web interface for the Multi-AI Agent Assistant with FastAPI backend.

## 🚀 Quick Start

### Option 1: Automatic Setup (Recommended)
```bash
# Run the startup script
start.bat
```

### Option 2: Manual Setup

#### Backend (Terminal 1)
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start FastAPI backend
python backend.py
```

#### Frontend (Terminal 2)
```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start React development server
npm start
```

## 📱 Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🎨 Features

- **Modern React UI** with matte black/gray design
- **Real-time chat interface** with Simi.ai
- **Quick action buttons** for common tasks
- **Auto-resizing input** with keyboard shortcuts
- **Responsive design** for all devices
- **FastAPI backend** with automatic documentation

## 🛠 Tech Stack

- **Frontend**: React 18, CSS3, Axios
- **Backend**: FastAPI, Python 3.12
- **AI**: GROQ API, LangGraph
- **Email**: Gmail API integration

## 📧 Gmail Setup

1. Follow instructions in `GMAIL_SETUP.md`
2. Place `credentials.json` in the project root
3. First email will prompt for Gmail authorization

## 🔧 Development

### Frontend Development
```bash
cd frontend
npm start          # Development server
npm run build      # Production build
```

### Backend Development
```bash
python backend.py  # Start with auto-reload
```

## 📝 Available Commands

- **Email**: "send mail to user@example.com"
- **Tasks**: "create task [description]"
- **Calendar**: "schedule meeting"
- **Analytics**: "analyze data"

## 🚨 Troubleshooting

1. **Port conflicts**: Change ports in backend.py (8000) or package.json (3000)
2. **CORS errors**: Ensure backend is running before frontend
3. **Gmail issues**: Check credentials.json and token.json files