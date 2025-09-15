# FastAPI Backend & MongoDB Schema Refactoring - Integration Guide

This guide provides step-by-step instructions for integrating the refactored multi-user system with RBAC into your existing FastAPI backend.

## Overview

The refactoring eliminates the generic `users` collection and implements a role-based access control (RBAC) system with separate `customers` and `Admins` collections. The system now supports:

- **Separate user types**: Customers and Admins with distinct authentication flows
- **Role-based permissions**: Super Admin and Admin roles with granular permissions
- **Enhanced security**: Proper data segregation and access control
- **Backward compatibility**: Migration script to transfer existing data

## Step 1: Update Configuration

### Update `app/core/config.py`

Add the new permissions configuration:

```python
# Add to your existing config
class Settings(BaseSettings):
    # ... existing settings ...
    
    # RBAC Settings
    default_SuperAdmin_email: str = "admin@example.com"
    default_SuperAdmin_password: str = "changeme123"
    
    # JWT Settings (if not already present)
    jwt_secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30 * 24 * 60  # 30 days
```

## Step 2: Update Main Application

### Update `main.py`

Replace the current route imports with the refactored versions:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.infrastructure.database import init_db

# Import refactored routes
from app.api.routes.auth_refactored import router as auth_router
from app.api.routes.chat_refactored import router as chat_router
from app.api.routes.tickets_refactored import router as tickets_router
from app.api.routes.admin_refactored import router as admin_router
from app.api.routes.knowledge_base import router as kb_router
from app.api.routes.upload import router as upload_router

app = FastAPI(title="Sally Chat Bot API", version="2.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include refactored routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(tickets_router, prefix="/api", tags=["Tickets"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(kb_router, prefix="/api/kb", tags=["Knowledge Base"])
app.include_router(upload_router, prefix="/api", tags=["Upload"])

@app.on_event("startup")
async def startup_event():
    """Initialize database and create default roles."""
    await init_db()
    
    # Create default roles if they don't exist
    from app.core.permissions import create_default_roles
    await create_default_roles()
    
    # Create default super Admin if no Admins exist
    from app.domain.entities_refactored import Admin
    admin_count = await Admin.find_all().count()
    if admin_count == 0:
        from app.core.security import get_password_hash
        default_admin = Admin(
            email=settings.default_SuperAdmin_email,
            hashed_password=get_password_hash(settings.default_SuperAdmin_password),
            full_name="Default Super Admin",
            role_id=None  # Will be set to SuperAdmin role
        )
        await default_admin.insert()
        print(f"Created default super Admin: {settings.default_SuperAdmin_email}")

@app.get("/")
async def root():
    return {"message": "Sally Chat Bot API v2.0 - Multi-User System with RBAC"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Step 3: Database Migration

### Run the Migration Script

1. **Backup your database** before running the migration
2. **Test the migration** in a development environment first
3. **Run the migration**:

```bash
cd sally-backend
python migrate_users_to_new_system.py
```

The migration script will:
- Create default roles (`SuperAdmin`, `Admin`)
- Migrate users to appropriate collections based on their role
- Update all related collections with new references
- Provide detailed logging of the migration process

### Migration Output Example:
```
INFO:root:Creating default roles...
INFO:root:Created role: SuperAdmin
INFO:root:Created role: Admin
INFO:root:Starting user migration...
INFO:root:Found 150 users to migrate
INFO:root:Migrated user john@example.com to Admin collection
INFO:root:Migrated user jane@example.com to customer collection
INFO:root:Migration complete: 5 Admins, 145 customers
INFO:root:Updating related collections...
INFO:root:Updated 200 conversations
INFO:root:Updated 50 tickets
INFO:root:Updated 150 ticket replies
INFO:root:Updated 25 knowledge base articles
INFO:root:Updated 300 activity logs
INFO:root:Migration successful!
```

## Step 4: Update Frontend Authentication

### Update Authentication Service

Update your frontend authentication service to handle the new token structure:

```typescript
// services/authService.ts
interface AuthResponse {
    access_token: string;
    token_type: string;
    user_type: 'Customer' | 'Admin';
    user: Customer | Admin;
}

interface Customer {
    id: string;
    email: string;
    full_name: string;
    is_active: boolean;
}

interface Admin {
    id: string;
    email: string;
    full_name: string;
    role: {
        id: string;
        name: string;
        permissions: string[];
    };
    is_active: boolean;
}
```

## Step 5: API Endpoint Changes

### New Authentication Endpoints

- `POST /api/auth/customer/login` - Customer login
- `POST /api/auth/admin/login` - Admin login  
- `POST /api/auth/customer/register` - Customer registration
- `POST /api/auth/admin/register` - Super Admin creates Admin accounts

### Updated Chat Endpoints

- `GET /api/chats` - Get customer conversations (requires customer auth)
- `GET /api/chats/{chat_id}/messages` - Get conversation messages with ownership validation
- `POST /api/chats/send` - Send message with proper user context

### Updated Ticket Endpoints

- `POST /api/tickets` - Create ticket (customer auth required)
- `GET /api/tickets` - Get customer tickets
- `GET /api/tickets/{ticket_id}` - Get specific ticket with ownership validation
- `POST /api/tickets/{ticket_id}/replies` - Add reply to ticket

### New admin Endpoints

- `GET /api/admin/admins` - List all Admins (Super Admin only)
- `POST /api/admin/admins` - Create Admin (Super Admin only)
- `PUT /api/admin/admins/{admin_id}` - Update Admin
- `DELETE /api/admin/admins/{admin_id}` - Delete Admin
- `GET /api/admin/customers` - List all customers
- `PUT /api/admin/customers/{customer_id}` - Update customer
- `GET /api/admin/roles` - List all roles
- `POST /api/admin/roles` - Create role
- `PUT /api/admin/roles/{role_id}` - Update role

## Step 6: Testing the Refactored System

### Test Authentication Flows

1. **Customer Registration and Login**
```bash
# Register new customer
curl -X POST http://localhost:8000/api/auth/customer/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123", "full_name": "Test User"}'

# Login as customer
curl -X POST http://localhost:8000/api/auth/customer/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=password123"
```

2. **admin Login**
```bash
# Login as admin
curl -X POST http://localhost:8000/api/auth/admin/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=changeme123"
```

### Test Customer Features

1. **Create and View Tickets**
```bash
# Create ticket (requires customer auth token)
curl -X POST http://localhost:8000/api/tickets \
  -H "Authorization: Bearer YOUR_CUSTOMER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Issue", "description": "This is a test ticket"}'

# Get customer tickets
curl -X GET http://localhost:8000/api/tickets \
  -H "Authorization: Bearer YOUR_CUSTOMER_TOKEN"
```

2. **Chat Functionality**
```bash
# Send message as customer
curl -X POST http://localhost:8000/api/chats/send \
  -H "Authorization: Bearer YOUR_CUSTOMER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello, I need help"}'
```

### Test admin Features

1. **View All Tickets**
```bash
# Get all tickets (requires admin auth token)
curl -X GET http://localhost:8000/api/admin/tickets \
  -H "Authorization: Bearer YOUR_admin_TOKEN"
```

2. **admin Management (Super admin only)**
```bash
# Create new admin (requires super admin token)
curl -X POST http://localhost:8000/api/admin/admins \
  -H "Authorization: Bearer YOUR_SuperAdmin_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newadmin@example.com", 
    "password": "newpassword123", 
    "full_name": "New admin",
    "role_id": "ROLE_OBJECT_ID"
  }'
```

## Step 7: Security Considerations

### Data Validation and Sanitization

The refactored system includes enhanced security measures:

1. **Proper ObjectId validation** for all database references
2. **Role-based access control** with granular permissions
3. **Data ownership validation** for all customer-specific endpoints
4. **Input sanitization** for chat messages and ticket content

### Permission System

The new permission system includes:

- `manage_admins` - Create, update, delete Admin accounts
- `view_all_tickets` - View all support tickets
- `reply_tickets` - Reply to tickets
- `assign_tickets` - Assign tickets to Admins
- `manage_ticket_statuses` - Update ticket statuses
- `manage_kb_articles` - Manage knowledge base articles
- `view_customers` - View customer information
- `manage_customers` - Update customer accounts
- `view_activity_logs` - View system activity logs

## Step 8: Rollback Plan

If you need to rollback the migration:

1. **Stop the application**
2. **Restore database backup**
3. **Revert code changes** to use the original user-based system
4. **Restart the application**

The migration script includes a `rollback()` method for testing purposes, but always rely on proper database backups for production rollbacks.

## Troubleshooting

### Common Issues

1. **"Role not found" errors**: Ensure you run the migration script to create default roles
2. **"Invalid ObjectId format"**: Check that all ObjectId references are properly formatted
3. **Authentication failures**: Verify JWT secret key configuration and token expiration settings

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Considerations

The refactored system is designed for scalability:

- **Indexed fields**: All user lookups use indexed email fields
- **Efficient queries**: Role-based queries minimize database lookups
- **Caching opportunities**: Role permissions can be cached to reduce database queries

## Next Steps

After successful integration:

1. **Update frontend components** to handle new user types
2. **Implement additional Admin features** using the new RBAC system
3. **Add monitoring and logging** for the new permission system
4. **Consider implementing API rate limiting** per user type
5. **Set up automated testing** for the new authentication flows

For questions or issues, refer to the detailed code documentation in each module.