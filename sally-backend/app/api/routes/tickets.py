from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.domain.entities import Ticket, TicketReply, TicketStatus, User, ActivityLog
from app.api.dependencies import get_current_customer, get_current_admin

router = APIRouter()


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
    user_id: str
    is_internal: bool
    created_at: datetime


@router.post("/", response_model=TicketResponse)
async def create_ticket(
    ticket_data: TicketCreate,
    current_user: User = Depends(get_current_customer)
):
    """Create a new support ticket."""
    ticket = Ticket(
        customer_id=str(current_user.id),
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
        assigned_to=ticket.assigned_to
    )


@router.get("/", response_model=List[TicketResponse])
async def get_user_tickets(current_user: User = Depends(get_current_customer)):
    """Get current user's tickets."""
    tickets = await Ticket.find(
        Ticket.customer_id == str(current_user.id)
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
            assigned_to=ticket.assigned_to
        )
        for ticket in tickets
    ]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_customer)
):
    """Get a specific ticket."""
    ticket = await Ticket.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check if user owns the ticket or is admin
    if ticket.customer_id != str(current_user.id) and current_user.role.value not in ["Admin", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return TicketResponse(
        id=str(ticket.id),
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        assigned_to=ticket.assigned_to
    )


@router.post("/{ticket_id}/replies", response_model=TicketReplyResponse)
async def add_ticket_reply(
    ticket_id: str,
    reply_data: TicketReplyCreate,
    current_user: User = Depends(get_current_customer)
):
    """Add a reply to a ticket."""
    ticket = await Ticket.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check access permissions
    if ticket.customer_id != str(current_user.id) and current_user.role.value not in ["Admin", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    reply = TicketReply(
        ticket_id=ticket_id,
        user_id=str(current_user.id),
        content=reply_data.content,
        is_internal=reply_data.is_internal
    )
    
    await reply.insert()
    
    # Update ticket status if customer replied
    if ticket.customer_id == str(current_user.id) and ticket.status == TicketStatus.RESOLVED:
        ticket.status = TicketStatus.OPEN
        await ticket.save()
    
    return TicketReplyResponse(
        id=str(reply.id),
        content=reply.content,
        user_id=reply.user_id,
        is_internal=reply.is_internal,
        created_at=reply.created_at
    )


@router.get("/{ticket_id}/replies", response_model=List[TicketReplyResponse])
async def get_ticket_replies(
    ticket_id: str,
    current_user: User = Depends(get_current_customer)
):
    """Get replies for a ticket."""
    ticket = await Ticket.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check access permissions
    if ticket.customer_id != str(current_user.id) and current_user.role.value not in ["Admin", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    replies = await TicketReply.find(
        TicketReply.ticket_id == ticket_id
    ).sort(TicketReply.created_at).to_list()
    
    # Filter internal replies for customers
    if current_user.role.value not in ["Admin", "SuperAdmin"]:
        replies = [reply for reply in replies if not reply.is_internal]
    
    return [
        TicketReplyResponse(
            id=str(reply.id),
            content=reply.content,
            user_id=reply.user_id,
            is_internal=reply.is_internal,
            created_at=reply.created_at
        )
        for reply in replies
    ]
