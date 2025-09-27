from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Union
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId
from fastapi.security import HTTPAuthorizationCredentials
from app.domain.entities_refactored import (
    Ticket, TicketReply, TicketStatus, Customer, Admin, ActivityLog
)
from app.core.permissions import get_current_customer, get_current_admin, get_current_admin_with_permission
from app.core.permissions import Permission, get_optional_auth_header, get_admin_from_token, get_current_customer_from_token

router = APIRouter()


# Dependency to get current customer or Admin
async def get_current_customer_or_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_optional_auth_header)
) -> Union[Customer, Admin]:
    """Get current authenticated user (either customer or Admin)."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Try Admin first
    admin = await get_admin_from_token(credentials.credentials)
    if admin:
        return admin
    
    # Try customer
    customer = await get_current_customer_from_token(credentials.credentials)
    if customer:
        return customer
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials"
    )


class TicketCreate(BaseModel):
    title: str
    description: str
    priority: str = "medium"


class TicketResponse(BaseModel):
    id: str
    title: str
    description: str
    status: TicketStatus
    priority: str
    created_at: datetime
    updated_at: datetime
    assigned_to: Optional[str] = None


class TicketReplyCreate(BaseModel):
    content: str
    is_internal: bool = False


class TicketReplyResponse(BaseModel):
    id: str
    content: str
    author_type: str  # "customer" or "admin"
    author_id: str
    author_name: Optional[str] = None  # Will be populated from customer/admin data
    is_internal: bool
    created_at: datetime


@router.post("/", response_model=TicketResponse)
async def create_ticket(
    ticket_data: TicketCreate,
    current_customer: Customer = Depends(get_current_customer)
):
    """Create a new support ticket."""
    ticket = Ticket(
        customer_id=current_customer.id,
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority
    )
    
    await ticket.insert()
    
    return TicketResponse(
        id=str(ticket.id),
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        assigned_to=str(ticket.assigned_to) if ticket.assigned_to else None
    )


@router.get("/", response_model=List[TicketResponse])
async def get_user_tickets(current_customer: Customer = Depends(get_current_customer)):
    """Get current customer's tickets."""
    tickets = await Ticket.find(
        Ticket.customer_id == current_customer.id
    ).sort(-Ticket.updated_at).to_list()
    
    return [
        TicketResponse(
            id=str(ticket.id),
            title=ticket.title,
            description=ticket.description,
            status=ticket.status,
            priority=ticket.priority,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            assigned_to=str(ticket.assigned_to) if ticket.assigned_to else None
        )
        for ticket in tickets
    ]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    current_user: Union[Customer, Admin] = Depends(get_current_customer_or_admin)
):
    """Get a specific ticket."""
    ticket = await Ticket.get(ObjectId(ticket_id))
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check if user owns the ticket or is Admin
    if isinstance(current_user, Customer) and ticket.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return TicketResponse(
        id=str(ticket.id),
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        assigned_to=str(ticket.assigned_to) if ticket.assigned_to else None
    )


@router.post("/{ticket_id}/replies", response_model=TicketReplyResponse)
async def add_ticket_reply(
    ticket_id: str,
    reply_data: TicketReplyCreate,
    current_user: Union[Customer, Admin] = Depends(get_current_customer_or_admin)
):
    """Add a reply to a ticket."""
    ticket = await Ticket.get(ObjectId(ticket_id))
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check access permissions
    if isinstance(current_user, Customer) and ticket.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Determine reply type and author
    if isinstance(current_user, Customer):
        reply = TicketReply(
            ticket_id=ticket.id,
            customer_id=current_user.id,
            content=reply_data.content,
            is_internal=False  # Customers cannot create internal replies
        )
        author_type = "customer"
        author_name = current_user.full_name
    else:
        # Admin reply
        reply = TicketReply(
            ticket_id=ticket.id,
            admin_id=current_user.id,
            content=reply_data.content,
            is_internal=reply_data.is_internal
        )
        author_type = "Admin"
        author_name = current_user.full_name
    
    await reply.insert()
    
    # Update ticket status if customer replied
    if isinstance(current_user, Customer) and ticket.status == TicketStatus.RESOLVED:
        ticket.status = TicketStatus.OPEN
        await ticket.save()
    
    # Log activity for Admin replies
    if isinstance(current_user, Admin):
        activity_log = ActivityLog(
            admin_id=current_user.id,
            action="reply_ticket",
            resource_type="ticket",
            resource_id=str(ticket.id),
            details={"reply_type": "Admin", "is_internal": reply_data.is_internal}
        )
        await activity_log.insert()
    
    return TicketReplyResponse(
        id=str(reply.id),
        content=reply.content,
        author_type=author_type,
        author_id=str(current_user.id),
        author_name=author_name,
        is_internal=reply.is_internal,
        created_at=reply.created_at
    )


@router.get("/{ticket_id}/replies", response_model=List[TicketReplyResponse])
async def get_ticket_replies(
    ticket_id: str,
    current_user: Union[Customer, Admin] = Depends(get_current_customer_or_admin)
):
    """Get replies for a ticket."""
    ticket = await Ticket.get(ObjectId(ticket_id))
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check access permissions
    if isinstance(current_user, Customer) and ticket.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    replies = await TicketReply.find(
        TicketReply.ticket_id == ticket.id
    ).sort(TicketReply.created_at).to_list()
    
    # Filter internal replies for customers
    if isinstance(current_user, Customer):
        replies = [reply for reply in replies if not reply.is_internal]
    
    # Build response with author information
    result = []
    for reply in replies:
        author_type = "Customer" if reply.customer_id else "Admin"
        author_name = None
        
        if reply.customer_id:
            customer = await Customer.get(reply.customer_id)
            if customer:
                author_name = customer.full_name
        elif reply.admin_id:
            admin = await admin.get(reply.admin_id)
            if admin:
                author_name = admin.full_name
        
        result.append(TicketReplyResponse(
            id=str(reply.id),
            content=reply.content,
            author_type=author_type,
            author_id=str(reply.customer_id or reply.admin_id),
            author_name=author_name,
            is_internal=reply.is_internal,
            created_at=reply.created_at
        ))
    
    return result


# admin endpoints for ticket management
@router.get("/admin/all", response_model=List[TicketResponse])
async def get_all_tickets(
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_ALL_TICKETS))
):
    """Get all support tickets (admin only)."""
    tickets = await Ticket.find_all().sort(-Ticket.updated_at).to_list()
    
    return [
        TicketResponse(
            id=str(ticket.id),
            title=ticket.title,
            description=ticket.description,
            status=ticket.status,
            priority=ticket.priority,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            assigned_to=str(ticket.assigned_to) if ticket.assigned_to else None
        )
        for ticket in tickets
    ]


@router.put("/admin/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: str,
    assigned_to: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.ASSIGN_TICKETS))
):
    """Assign a ticket to an admin."""
    ticket = await Ticket.get(ObjectId(ticket_id))
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Validate assigned admin if provided
    if assigned_to:
        try:
            admin_id = ObjectId(assigned_to)
            assigned_admin = await Admin.get(admin_id)
            if not assigned_admin:
                raise HTTPException(status_code=400, detail="Invalid admin ID")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid admin ID format")
        
        ticket.assigned_to = admin_id
    else:
        ticket.assigned_to = None
    
    await ticket.save()
    
    # Log activity
    activity_log = ActivityLog(
        admin_id=current_admin.id,
        action="assign_ticket",
        resource_type="ticket",
        resource_id=str(ticket.id),
        details={"assigned_to": assigned_to}
    )
    await activity_log.insert()
    
    return {"message": "Ticket assignment updated"}


@router.put("/admin/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    status_data: dict,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_TICKET_STATUSES))
):
    """Update ticket status."""
    ticket = await Ticket.get(ObjectId(ticket_id))
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    new_status = status_data.get("status")
    if new_status not in ["open", "in_progress", "resolved", "closed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    old_status = ticket.status
    ticket.status = TicketStatus(new_status)
    await ticket.save()
    
    # Log activity
    activity_log = ActivityLog(
        admin_id=current_admin.id,
        action="update_ticket_status",
        resource_type="ticket",
        resource_id=str(ticket.id),
        details={"new_status": new_status, "old_status": old_status}
    )
    await activity_log.insert()
    
    return {"message": "Ticket status updated successfully"}

