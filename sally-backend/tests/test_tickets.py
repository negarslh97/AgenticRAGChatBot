"""
Tests for ticket management functionality.
"""
import pytest
from httpx import AsyncClient


class TestTicketCreation:
    """Test ticket creation functionality."""

    @pytest.mark.asyncio
    async def test_customer_can_create_ticket(self, client: AsyncClient, customer_user, customer_token, auth_headers, faker):
        """Test that a customer can create a new ticket."""
        ticket_data = {
            "title": faker.sentence(),
            "description": faker.paragraph(),
            "priority": "high"
        }

        headers = auth_headers(customer_token)
        response = await client.post("/api/customer/tickets/", json=ticket_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == ticket_data["title"]
        assert data["description"] == ticket_data["description"]
        assert data["priority"] == ticket_data["priority"]
        assert data["status"] == "open"
        assert "id" in data
        assert data["assigned_to"] is None

    @pytest.mark.asyncio
    async def test_guest_cannot_create_ticket(self, client: AsyncClient, faker):
        """Test that unauthenticated users cannot create tickets."""
        ticket_data = {
            "title": faker.sentence(),
            "description": faker.paragraph(),
            "priority": "medium"
        }

        response = await client.post("/api/customer/tickets/", json=ticket_data)

        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_cannot_create_ticket_as_customer(self, client: AsyncClient, admin_user, admin_token, auth_headers, faker):
        """Test that admins cannot create tickets through customer endpoints."""
        ticket_data = {
            "title": faker.sentence(),
            "description": faker.paragraph(),
            "priority": "medium"
        }

        headers = auth_headers(admin_token)
        response = await client.post("/api/customer/tickets/", json=ticket_data, headers=headers)

        # This should fail because admin token is not valid for customer endpoints
        assert response.status_code == 401


class TestTicketReplies:
    """Test ticket reply functionality."""

    @pytest.mark.asyncio
    async def test_customer_can_reply_to_own_ticket(self, client: AsyncClient, customer_user, customer_token, auth_headers, test_ticket, faker):
        """Test that a customer can reply to their own ticket."""
        reply_data = {
            "content": faker.paragraph(),
            "is_internal": False
        }

        headers = auth_headers(customer_token)
        response = await client.post(
            f"/api/customer/tickets/{test_ticket.id}/replies",
            json=reply_data,
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == reply_data["content"]
        assert data["author_type"] == "customer"
        assert data["author_id"] == str(customer_user.id)
        assert data["is_internal"] is False

    @pytest.mark.asyncio
    async def test_customer_cannot_reply_to_other_ticket(self, client: AsyncClient, customer_user, customer_token, auth_headers, faker):
        """Test that a customer cannot reply to tickets they don't own."""
        # Create another customer and their ticket
        from app.domain.entities import Customer, Ticket

        other_customer = Customer(
            email=faker.email(),
            hashed_password="hashed_password",
            full_name=faker.name()
        )
        await other_customer.insert()

        other_ticket = Ticket(
            customer_id=str(other_customer.id),
            title=faker.sentence(),
            description=faker.paragraph()
        )
        await other_ticket.insert()

        reply_data = {
            "content": faker.paragraph(),
            "is_internal": False
        }

        headers = auth_headers(customer_token)
        response = await client.post(
            f"/api/customer/tickets/{other_ticket.id}/replies",
            json=reply_data,
            headers=headers
        )

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_customer_cannot_create_internal_reply(self, client: AsyncClient, customer_user, customer_token, auth_headers, test_ticket, faker):
        """Test that customers cannot create internal replies."""
        reply_data = {
            "content": faker.paragraph(),
            "is_internal": True  # Customers should not be able to set this to True
        }

        headers = auth_headers(customer_token)
        response = await client.post(
            f"/api/customer/tickets/{test_ticket.id}/replies",
            json=reply_data,
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        # The reply should be created but is_internal should be False regardless of input
        assert data["is_internal"] is False

    @pytest.mark.asyncio
    async def test_admin_can_reply_to_any_ticket(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_ticket, faker):
        """Test that an admin can reply to any ticket."""
        reply_data = {
            "content": faker.paragraph(),
            "is_internal": True
        }

        headers = auth_headers(admin_token)
        response = await client.post(
            f"/api/customer/tickets/{test_ticket.id}/replies",
            json=reply_data,
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == reply_data["content"]
        assert data["author_type"] == "Admin"
        assert data["author_id"] == str(admin_user.id)
        assert data["is_internal"] is True


class TestTicketViewing:
    """Test ticket viewing permissions."""

    @pytest.mark.asyncio
    async def test_customer_can_view_own_tickets(self, client: AsyncClient, customer_user, customer_token, auth_headers):
        """Test that customers can view their own tickets."""
        headers = auth_headers(customer_token)
        response = await client.get("/api/customer/tickets/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned tickets should belong to this customer
        for ticket in data:
            assert ticket["assigned_to"] is None or isinstance(ticket["assigned_to"], str)

    @pytest.mark.asyncio
    async def test_customer_can_view_specific_own_ticket(self, client: AsyncClient, customer_user, customer_token, auth_headers, test_ticket):
        """Test that customers can view a specific ticket they own."""
        headers = auth_headers(customer_token)
        response = await client.get(f"/api/customer/tickets/{test_ticket.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_ticket.id)
        assert data["title"] == test_ticket.title
        assert data["description"] == test_ticket.description

    @pytest.mark.asyncio
    async def test_customer_cannot_view_other_ticket(self, client: AsyncClient, customer_user, customer_token, auth_headers, faker):
        """Test that customers cannot view tickets they don't own."""
        # Create another customer and their ticket
        from app.domain.entities import Customer, Ticket

        other_customer = Customer(
            email=faker.email(),
            hashed_password="hashed_password",
            full_name=faker.name()
        )
        await other_customer.insert()

        other_ticket = Ticket(
            customer_id=str(other_customer.id),
            title=faker.sentence(),
            description=faker.paragraph()
        )
        await other_ticket.insert()

        headers = auth_headers(customer_token)
        response = await client.get(f"/api/customer/tickets/{other_ticket.id}", headers=headers)

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_can_view_all_tickets(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_ticket):
        """Test that admins can view all tickets."""
        headers = auth_headers(admin_token)
        response = await client.get("/api/admin/tickets/all", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least our test ticket should be there

        # Verify our test ticket is in the list
        ticket_ids = [ticket["id"] for ticket in data]
        assert str(test_ticket.id) in ticket_ids

    @pytest.mark.asyncio
    async def test_admin_can_view_specific_ticket(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_ticket):
        """Test that admins can view any specific ticket."""
        headers = auth_headers(admin_token)
        response = await client.get(f"/api/customer/tickets/{test_ticket.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_ticket.id)
        assert data["title"] == test_ticket.title


class TestTicketRepliesViewing:
    """Test ticket replies viewing permissions."""

    @pytest.mark.asyncio
    async def test_customer_can_view_replies_on_own_ticket(self, client: AsyncClient, customer_user, customer_token, auth_headers, test_ticket):
        """Test that customers can view replies on their own tickets."""
        headers = auth_headers(customer_token)
        response = await client.get(f"/api/customer/tickets/{test_ticket.id}/replies", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_customer_cannot_view_internal_replies(self, client: AsyncClient, customer_user, customer_token, auth_headers, test_ticket, admin_user, faker):
        """Test that customers cannot see internal replies."""
        # First create an internal reply as admin
        from app.domain.entities import TicketReply

        internal_reply = TicketReply(
            ticket_id=str(test_ticket.id),
            admin_id=str(admin_user.id),
            content=faker.paragraph(),
            is_internal=True
        )
        await internal_reply.insert()

        # Also create a public reply
        public_reply = TicketReply(
            ticket_id=str(test_ticket.id),
            admin_id=str(admin_user.id),
            content=faker.paragraph(),
            is_internal=False
        )
        await public_reply.insert()

        headers = auth_headers(customer_token)
        response = await client.get(f"/api/customer/tickets/{test_ticket.id}/replies", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Customer should only see public replies
        reply_ids = [reply["id"] for reply in data]
        assert str(public_reply.id) in reply_ids
        assert str(internal_reply.id) not in reply_ids

    @pytest.mark.asyncio
    async def test_admin_can_view_all_replies(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_ticket, faker):
        """Test that admins can view all replies including internal ones."""
        # Create replies as before
        from app.domain.entities import TicketReply

        internal_reply = TicketReply(
            ticket_id=str(test_ticket.id),
            admin_id=str(admin_user.id),
            content=faker.paragraph(),
            is_internal=True
        )
        await internal_reply.insert()

        public_reply = TicketReply(
            ticket_id=str(test_ticket.id),
            admin_id=str(admin_user.id),
            content=faker.paragraph(),
            is_internal=False
        )
        await public_reply.insert()

        headers = auth_headers(admin_token)
        response = await client.get(f"/api/customer/tickets/{test_ticket.id}/replies", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Admin should see all replies
        reply_ids = [reply["id"] for reply in data]
        assert str(public_reply.id) in reply_ids
        assert str(internal_reply.id) in reply_ids


class TestTicketAssignment:
    """Test ticket assignment functionality."""

    @pytest.mark.asyncio
    async def test_admin_can_assign_ticket(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_ticket):
        """Test that admins can assign tickets to themselves."""
        headers = auth_headers(admin_token)
        response = await client.put(
            f"/api/admin/tickets/{test_ticket.id}/assign",
            json={"assigned_to": str(admin_user.id)},
            headers=headers
        )

        assert response.status_code == 200
        assert "Ticket assignment updated" in response.json()["message"]

        # Verify assignment
        updated_ticket = await client.get(f"/api/customer/tickets/{test_ticket.id}", headers=headers)
        assert updated_ticket.status_code == 200
        assert updated_ticket.json()["assigned_to"] == str(admin_user.id)

    @pytest.mark.asyncio
    async def test_admin_can_unassign_ticket(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_ticket):
        """Test that admins can unassign tickets."""
        # First assign the ticket
        headers = auth_headers(admin_token)
        assign_response = await client.put(
            f"/api/admin/tickets/{test_ticket.id}/assign",
            json={"assigned_to": str(admin_user.id)},
            headers=headers
        )
        assert assign_response.status_code == 200

        # Now unassign it
        unassign_response = await client.put(
            f"/api/admin/tickets/{test_ticket.id}/assign",
            json={"assigned_to": None},
            headers=headers
        )
        assert unassign_response.status_code == 200

        # Verify unassignment
        updated_ticket = await client.get(f"/api/customer/tickets/{test_ticket.id}", headers=headers)
        assert updated_ticket.status_code == 200
        assert updated_ticket.json()["assigned_to"] is None

    @pytest.mark.asyncio
    async def test_customer_cannot_assign_ticket(self, client: AsyncClient, customer_user, customer_token, auth_headers, test_ticket):
        """Test that customers cannot assign tickets."""
        headers = auth_headers(customer_token)
        response = await client.put(
            f"/api/admin/tickets/{test_ticket.id}/assign",
            json={"assigned_to": str(customer_user.id)},
            headers=headers
        )

        # Should fail with 401 because customer token is not valid for admin endpoints
        assert response.status_code == 401


class TestTicketStatusManagement:
    """Test ticket status management functionality."""

    @pytest.mark.asyncio
    async def test_admin_can_change_ticket_status(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_ticket):
        """Test that admins can change ticket status."""
        headers = auth_headers(admin_token)
        response = await client.put(
            f"/api/admin/tickets/{test_ticket.id}/status",
            json={"status": "in_progress"},
            headers=headers
        )

        assert response.status_code == 200
        assert "Ticket status updated successfully" in response.json()["message"]

        # Verify status change
        updated_ticket = await client.get(f"/api/customer/tickets/{test_ticket.id}", headers=headers)
        assert updated_ticket.status_code == 200
        assert updated_ticket.json()["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_admin_cannot_set_invalid_status(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_ticket):
        """Test that admins cannot set invalid ticket status."""
        headers = auth_headers(admin_token)
        response = await client.put(
            f"/api/admin/tickets/{test_ticket.id}/status",
            json={"status": "invalid_status"},
            headers=headers
        )

        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_customer_reply_changes_resolved_ticket_to_open(self, client: AsyncClient, customer_user, customer_token, admin_token, auth_headers, test_ticket, admin_user, faker):
        """Test that when a customer replies to a resolved ticket, it reopens."""
        # First, set ticket to resolved as admin
        headers = auth_headers(admin_token)
        status_response = await client.put(
            f"/api/admin/tickets/{test_ticket.id}/status",
            json={"status": "resolved"},
            headers=headers
        )
        assert status_response.status_code == 200

        # Verify ticket is resolved
        ticket_response = await client.get(f"/api/customer/tickets/{test_ticket.id}", headers=headers)
        assert ticket_response.json()["status"] == "resolved"

        # Now customer replies
        customer_headers = auth_headers(customer_token)
        reply_data = {
            "content": faker.paragraph(),
            "is_internal": False
        }
        reply_response = await client.post(
            f"/api/customer/tickets/{test_ticket.id}/replies",
            json=reply_data,
            headers=customer_headers
        )
        assert reply_response.status_code == 200

        # Verify ticket status changed back to open
        updated_ticket = await client.get(f"/api/customer/tickets/{test_ticket.id}", headers=headers)
        assert updated_ticket.json()["status"] == "open"
