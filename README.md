# 🚀 Sally ChatBot - AI-Powered Customer Support Platform

![Sally ChatBot](https://img.shields.io/badge/Sally%20ChatBot-AI%20Support-4CAF50) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-blue) ![React](https://img.shields.io/badge/React-18.2.0-61DAFB) ![MongoDB](https://img.shields.io/badge/MongoDB-7.0-green)

## 📋 Overview

Sally ChatBot is an advanced AI-powered customer support platform built with modern web technologies. It features real-time chat, RAG-based AI responses, comprehensive admin panel, and knowledge base management.

## ✨ Features

### 🎯 Core Features
- **Real-time Chat** with WebSocket support
- **RAG-powered AI** responses using OpenAI
- **Multi-role Authentication** (Customer, Admin, Super Admin)
- **Ticket Management System** for support requests
- **Knowledge Base** for self-service support
- **Admin Panel** for comprehensive management
- **File Upload** support for documents and images

### 🔧 Technical Features
- **FastAPI Backend** with automatic API documentation
- **React Frontend** with TypeScript
- **MongoDB Database** with Beanie ODM
- **JWT Authentication** with RBAC
- **WebSocket Support** for real-time communication
- **Responsive Design** with Tailwind CSS
- **RTL Support** for Persian language

## 🏗️ Architecture

```
SallyBot/
├── sally-backend/          # FastAPI Backend
│   ├── app/
│   │   ├── api/           # API Routes & Endpoints
│   │   ├── core/          # Core functionality (auth, config)
│   │   ├── domain/        # Business logic & models
│   │   └── infrastructure/# Infrastructure services
│   ├── tests/             # Unit tests
│   └── main.py            # Application entry point
├── sally-frontend/        # React Frontend
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── pages/         # Application pages
│   │   ├── services/      # API service layer
│   │   └── context/       # React contexts
│   └── public/            # Static assets
└── start_project.bat      # Quick start script
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- MongoDB (running locally)

### Method 1: Using Batch File (Recommended)
```bash
# Run in project root directory
start_project.bat
```

### Method 2: Manual Setup

#### Backend Setup
```bash
cd sally-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example)
# Edit .env with your configuration

# Run backend
python main.py
```

#### Frontend Setup
```bash
cd sally-frontend

# Install dependencies
npm install

# Start development server
npm start
```

### 🌐 Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Main application |
| **Backend API** | http://localhost:8000 | REST API |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **MongoDB** | mongodb://localhost:27017 | Database |

## 👤 Default Admin Account

After first run, a default admin account is created:

- **Email**: `admin@sally.com`
- **Password**: `admin123`
- **Role**: Super Admin

## 📚 API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - User logout

### Chat
- `POST /api/message` - Send chat message
- `GET /api/conversations` - Get conversations
- `WebSocket /api/ws` - Real-time chat


### Admin (Super Admin only)
- `GET /api/admin/superadmin/stats` - Dashboard statistics
- `GET /api/admin/admins` - Manage admin users
- `GET /api/admin/customers` - Manage customers

### Knowledge Base
- `GET /api/kb/articles` - Get published articles
- `POST /api/admin/kb/articles` - Create articles (Admin+)

## 🔧 Configuration

### Environment Variables

Create `.env` file in `sally-backend` directory:

```env
# Database
DATABASE_URL=mongodb://localhost:27017/SallyChatBot

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=43200

# Default Admin
DEFAULT_SUPERADMIN_EMAIL=admin@sally.com
DEFAULT_SUPERADMIN_PASSWORD=admin123

# OpenAI (Optional)
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

### MongoDB Setup

1. Install MongoDB locally
2. Create database: `SallyChatBot`
3. Default connection: `mongodb://localhost:27017/SallyChatBot`

## 🧪 Testing

```bash
# Backend tests
cd sally-backend
pytest tests/

# Frontend tests
cd sally-frontend
npm test
```

## 📱 Frontend Pages

- **/** - Home page
- **/login** - User login
- **/register** - User registration
- **/dashboard** - Customer dashboard
- **/admin** - Admin panel
- **/super-admin** - Super admin dashboard
- **/knowledge-base** - Knowledge base
- **/chat** - Chat interface

## 🔒 Security Features

- **JWT Authentication** with secure token handling
- **Role-Based Access Control** (RBAC)
- **Input Validation** with Pydantic models
- **CORS Protection** with configurable origins
- **Password Hashing** with bcrypt
- **Rate Limiting** for API endpoints

## 🎨 Customization

### Themes
The application supports both LTR and RTL layouts with Persian language support.

### Styling
- **Tailwind CSS** for utility-first styling
- **Custom Components** for consistent UI
- **Responsive Design** for all screen sizes
- **Dark/Light Mode** support

## 🚀 Deployment

### Production Setup

1. **Backend Deployment**
```bash
# Set production environment
DEBUG=false
DATABASE_URL=your-production-mongodb-url

# Use production WSGI server
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

2. **Frontend Build**
```bash
cd sally-frontend
npm run build
```

3. **Environment Setup**
- Use production MongoDB instance
- Set secure JWT_SECRET_KEY
- Configure proper CORS origins
- Enable HTTPS with SSL certificates

### Docker Deployment

```dockerfile
# Backend Dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Frontend Dockerfile
FROM node:18
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

## 📊 Monitoring

- **Application Logs** - Check console output
- **MongoDB Logs** - Database performance monitoring
- **API Metrics** - Request/response tracking
- **Error Tracking** - Exception handling and logging

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the API documentation at `/docs`
- Review the troubleshooting section
- Create an issue on GitHub

## 🙏 Acknowledgments

- **FastAPI** for the amazing web framework
- **React** for the frontend framework
- **MongoDB** for the database
- **OpenAI** for AI capabilities
- **Tailwind CSS** for styling

---

**Happy Coding! 🚀**

For more information, visit our [documentation](#) or contact the development team.