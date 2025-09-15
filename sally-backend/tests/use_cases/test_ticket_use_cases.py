import pytest
from unittest.mock import AsyncMock
from app.domain.entities import Ticket, TicketReply, TicketStatus
from app.use_cases.ticket_use_cases import TicketUseCases

@pytest.mark.asyncio
async def test_create_ticket(mocker):
    # Mock Ticket repository
    mock_ticket = mocker.MagicMock(spec=Ticket)
    mock_ticket.insert = AsyncMock()
    
    # Mock Ticket constructor
    mocker.patch('app.use_cases.ticket_use_cases.Ticket', return_value=mock_ticket)
    
    # Test data
    customer_id = "user123"
    title = "Login issue"
    description = "Can't login to account"
    priority = "high"
    
    # Call the method
    result = await TicketUseCases.create_ticket(customer_id, title, description, priority)
    
    # Assertions
    assert result == mock_ticket
    mock_ticket.insert.assert_called_once()

@pytest.mark.asyncio
async def test_add_reply(mocker):
    # Mock dependencies
    mock_reply = mocker.MagicMock(spec=TicketReply)
    mock_reply.insert = AsyncMock()
    mocker.patch('app.use_cases.ticket_use_cases.TicketReply', return_value=mock_reply)
    
    mock_ticket = mocker.MagicMock(spec=Ticket)
    mock_ticket.status = TicketStatus.RESOLVED
    mock_ticket.save = AsyncMock()
    mocker.patch('app.use_cases.ticket_use_cases.Ticket.get', AsyncMock(return_value=mock_ticket))
    
    # Test data
    ticket_id = "ticket123"
    user_id = "user456"
    content = "Have you tried resetting your password?"
    
    # Call the method
    result = await TicketUseCases.add_reply(ticket_id, user_id, content)
    
    # Assertions
    assert result == mock_reply
    mock_reply.insert.assert_called_once()
    mock_ticket.save.assert_called_once()
    assert mock_ticket.status == TicketStatus.OPEN

@pytest.mark.asyncio
async def test_get_ticket_by_id_found(mocker):
    # Mock Ticket repository
    mock_ticket = mocker.MagicMock(spec=Ticket)
    mocker.patch('app.use_cases.ticket_use_cases.Ticket.get', AsyncMock(return_value=mock_ticket))
    
    # Test data
    ticket_id = "ticket123"
    
    # Call the method
    result = await TicketUseCases.get_ticket_by_id(ticket_id)
    
    # Assertions
    assert result == mock_ticket

@pytest.mark.asyncio
async def test_get_ticket_by_id_not_found(mocker):
    # Mock Ticket repository to return None
    mocker.patch('app.use_cases.ticket_use_cases.Ticket.get', AsyncMock(return_value=None))
    
    # Test data
    ticket_id = "non_existent"
    
    # Call the method
    result = await TicketUseCases.get_ticket_by_id(ticket_id)
    
    # Assertions
    assert result is None

@pytest.mark.asyncio
async def test_update_ticket_status_success(mocker):
    # Mock Ticket repository
    mock_ticket = mocker.MagicMock(spec=Ticket)
    mock_ticket.save = AsyncMock()
    mocker.patch('app.use_cases.ticket_use_cases.Ticket.get', AsyncMock(return_value=mock_ticket))
    
    # Test data
    ticket_id = "ticket123"
    new_status = TicketStatus.CLOSED
    
    # Call the method
    result = await TicketUseCases.update_ticket_status(ticket_id, new_status)
    
    # Assertions
    assert result == mock_ticket
    assert mock_ticket.status == new_status
    mock_ticket.save.assert_called_once()

@pytest.mark.asyncio
async def test_update_ticket_status_not_found(mocker):
    # Mock Ticket repository to return None
    mocker.patch('app.use_cases.ticket_use_cases.Ticket.get', AsyncMock(return_value=None))
    
    # Test data
    ticket_id = "non_existent"
    new_status = TicketStatus.CLOSED
    
    # Call the method
    result = await TicketUseCases.update_ticket_status(ticket_id, new_status)
    
    # Assertions
    assert result is None