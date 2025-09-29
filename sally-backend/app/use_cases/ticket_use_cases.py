from typing import List, Optional
from app.domain.entities import Ticket, TicketReply, TicketStatus, User


class TicketUseCases:
    @staticmethod
    async def create_ticket(customer_id: str, title: str, description: str, priority: str = "medium") -> Ticket:
        """Create a new support ticket."""
        ticket = Ticket(
            customer_id=customer_id,
            title=title,
            description=description,
            priority=priority
        )
        
        await ticket.insert()
        return ticket
    
    @staticmethod
    async def get_user_tickets(user_id: str) -> List[Ticket]:
        """Get all tickets for a user."""
        return await Ticket.find(Ticket.customer_id == user_id).sort(-Ticket.updated_at).to_list()
    
    @staticmethod
    async def get_ticket_by_id(ticket_id: str) -> Optional[Ticket]:
        """Get ticket by ID."""
        return await Ticket.get(ticket_id)
    
    @staticmethod
    async def add_reply(ticket_id: str, user_id: str, content: str, is_internal: bool = False) -> TicketReply:
        """Add a reply to a ticket."""
        reply = TicketReply(
            ticket_id=ticket_id,
            user_id=user_id,
            content=content,
            is_internal=is_internal
        )
        
        await reply.insert()
        
        # Update ticket status if needed
        ticket = await Ticket.get(ticket_id)
        if ticket and ticket.status == TicketStatus.RESOLVED:
            ticket.status = TicketStatus.OPEN
            await ticket.save()
        
        return reply
    
    @staticmethod
    async def get_ticket_replies(ticket_id: str, include_internal: bool = False) -> List[TicketReply]:
        """Get replies for a ticket."""
        query = TicketReply.ticket_id == ticket_id
        
        if not include_internal:
            query = query & (TicketReply.is_internal == False)
        
        return await TicketReply.find(query).sort(TicketReply.created_at).to_list()
    
    @staticmethod
    async def update_ticket_status(ticket_id: str, status: TicketStatus) -> Optional[Ticket]:
        """Update ticket status."""
        ticket = await Ticket.get(ticket_id)
        if not ticket:
            return None
        
        ticket.status = status
        await ticket.save()
        return ticket
    
    @staticmethod
    async def assign_ticket(ticket_id: str, admin_id: Optional[str]) -> Optional[Ticket]:
        """Assign ticket to an admin."""
        ticket = await Ticket.get(ticket_id)
        if not ticket:
            return None
        
        ticket.assigned_to = admin_id
        await ticket.save()
        return ticket
