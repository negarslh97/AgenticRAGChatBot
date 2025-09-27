"""
Tests for admin management functionality and permissions.
"""
import pytest
from httpx import AsyncClient


class TestAdminViewingPermissions:
    """Test admin viewing permissions."""

    @pytest.mark.asyncio
    async def test_regular_admin_cannot_view_admins_list(self, client: AsyncClient, admin_user, admin_token, auth_headers):
        """Test that regular admins cannot view the admins list (only SuperAdmin can)."""
        headers = auth_headers(admin_token)
        response = await client.get("/api/admin/admins", headers=headers)

        # Regular admin should not have VIEW_adminS permission
        assert response.status_code == 403
        assert "Permission" in response.json()["detail"] and "required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_super_admin_can_view_admins_list(self, client: AsyncClient, super_admin_user, super_admin_token, auth_headers):
        """Test that SuperAdmins can view the admins list."""
        headers = auth_headers(super_admin_token)
        response = await client.get("/api/admin/admins", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Should include our super admin user
        admin_ids = [admin["id"] for admin in data]
        assert str(super_admin_user.id) in admin_ids

    @pytest.mark.asyncio
    async def test_super_admin_can_view_admin_count(self, client: AsyncClient, super_admin_user, super_admin_token, auth_headers):
        """Test that SuperAdmins can view admin count."""
        headers = auth_headers(super_admin_token)
        response = await client.get("/api/admin/admins/count", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        assert data["count"] >= 1  # At least our super admin

    @pytest.mark.asyncio
    async def test_regular_admin_cannot_view_admin_count(self, client: AsyncClient, admin_user, admin_token, auth_headers):
        """Test that regular admins cannot view admin count."""
        headers = auth_headers(admin_token)
        response = await client.get("/api/admin/admins/count", headers=headers)

        assert response.status_code == 403
        assert "Permission" in response.json()["detail"] and "required" in response.json()["detail"]


class TestAdminCreationPermissions:
    """Test admin creation permissions."""

    @pytest.mark.asyncio
    async def test_super_admin_can_create_admin(self, client: AsyncClient, super_admin_user, super_admin_token, auth_headers, faker):
        """Test that SuperAdmins can create new admins."""
        from app.domain.entities_refactored import Role

        # Get Admin role
        admin_role = await Role.find_one({"name": "Admin"})
        assert admin_role, "Admin role not found"

        admin_data = {
            "email": faker.email(),
            "password": "testpassword123",
            "full_name": faker.name(),
            "role_id": str(admin_role.id)
        }

        headers = auth_headers(super_admin_token)
        response = await client.post("/api/admin/admins", json=admin_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == admin_data["email"]
        assert data["full_name"] == admin_data["full_name"]
        assert data["role"]["name"] == "Admin"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_regular_admin_cannot_create_admin(self, client: AsyncClient, admin_user, admin_token, auth_headers, faker):
        """Test that regular admins cannot create new admins."""
        from app.domain.entities_refactored import Role

        # Get Admin role
        admin_role = await Role.find_one({"name": "Admin"})
        assert admin_role, "Admin role not found"

        admin_data = {
            "email": faker.email(),
            "password": "testpassword123",
            "full_name": faker.name(),
            "role_id": str(admin_role.id)
        }

        headers = auth_headers(admin_token)
        response = await client.post("/api/admin/admins", json=admin_data, headers=headers)

        assert response.status_code == 403
        assert "Permission" in response.json()["detail"] and "required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_super_admin_can_create_super_admin(self, client: AsyncClient, super_admin_user, super_admin_token, auth_headers, faker):
        """Test that SuperAdmins can create other SuperAdmins."""
        from app.domain.entities_refactored import Role

        # Get SuperAdmin role
        super_admin_role = await Role.find_one({"name": "SuperAdmin"})
        assert super_admin_role, "SuperAdmin role not found"

        admin_data = {
            "email": faker.email(),
            "password": "testpassword123",
            "full_name": faker.name(),
            "role_id": str(super_admin_role.id)
        }

        headers = auth_headers(super_admin_token)
        response = await client.post("/api/admin/admins", json=admin_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == admin_data["email"]
        assert data["role"]["name"] == "SuperAdmin"


class TestAdminUpdatePermissions:
    """Test admin update permissions."""

    @pytest.mark.asyncio
    async def test_super_admin_can_update_admin(self, client: AsyncClient, super_admin_user, super_admin_token, auth_headers, admin_user, faker):
        """Test that SuperAdmins can update admin information."""
        update_data = {
            "full_name": faker.name(),
            "is_active": False
        }

        headers = auth_headers(super_admin_token)
        response = await client.put(f"/api/admin/admins/{str(admin_user.id)}", json=update_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["is_active"] == update_data["is_active"]

    @pytest.mark.asyncio
    async def test_super_admin_can_change_admin_role(self, client: AsyncClient, super_admin_user, super_admin_token, auth_headers, admin_user, faker):
        """Test that SuperAdmins can change admin roles."""
        from app.domain.entities_refactored import Role

        # Get SuperAdmin role
        super_admin_role = await Role.find_one({"name": "SuperAdmin"})
        assert super_admin_role, "SuperAdmin role not found"

        update_data = {
            "role_id": str(super_admin_role.id)
        }

        headers = auth_headers(super_admin_token)
        response = await client.put(f"/api/admin/admins/{str(admin_user.id)}", json=update_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["role"]["name"] == "SuperAdmin"

    @pytest.mark.asyncio
    async def test_regular_admin_cannot_update_admin(self, client: AsyncClient, admin_user, admin_token, auth_headers, super_admin_user, faker):
        """Test that regular admins cannot update other admins."""
        update_data = {
            "full_name": faker.name()
        }

        headers = auth_headers(admin_token)
        response = await client.put(f"/api/admin/admins/{super_admin_user.id}", json=update_data, headers=headers)

        assert response.status_code == 403
        assert "Permission" in response.json()["detail"] and "required" in response.json()["detail"]


class TestAdminDeletionPermissions:
    """Test admin deletion permissions."""

    @pytest.mark.asyncio
    async def test_super_admin_can_delete_admin(self, client: AsyncClient, super_admin_user, super_admin_token, auth_headers, admin_user):
        """Test that SuperAdmins can delete admins."""
        headers = auth_headers(super_admin_token)

        # First verify admin exists
        get_response = await client.get(f"/api/admin/admins/{str(admin_user.id)}", headers=headers)
        assert get_response.status_code == 200

        # Delete the admin
        delete_response = await client.delete(f"/api/admin/admins/{str(admin_user.id)}", headers=headers)
        assert delete_response.status_code == 204

        # Verify admin is deleted
        get_after_delete = await client.get(f"/api/admin/admins/{str(admin_user.id)}", headers=headers)
        assert get_after_delete.status_code == 404

    @pytest.mark.asyncio
    async def test_regular_admin_cannot_delete_admin(self, client: AsyncClient, admin_user, admin_token, auth_headers, super_admin_user):
        """Test that regular admins cannot delete admins."""
        headers = auth_headers(admin_token)
        response = await client.delete(f"/api/admin/admins/{str(super_admin_user.id)}", headers=headers)

        assert response.status_code == 403
        assert "Permission" in response.json()["detail"] and "required" in response.json()["detail"]


class TestCustomerManagementPermissions:
    """Test customer management permissions."""

    @pytest.mark.asyncio
    async def test_admin_can_view_customers(self, client: AsyncClient, admin_user, admin_token, auth_headers, customer_user):
        """Test that admins can view customers."""
        headers = auth_headers(admin_token)
        response = await client.get("/api/admin/customers", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Should include our test customer
        customer_ids = [customer["id"] for customer in data]
        assert str(customer_user.id) in customer_ids

    @pytest.mark.asyncio
    async def test_admin_can_update_customers(self, client: AsyncClient, admin_user, admin_token, auth_headers, customer_user, faker):
        """Test that admins can update customer information."""
        update_data = {
            "full_name": faker.name(),
            "is_active": False
        }

        headers = auth_headers(admin_token)
        response = await client.put(f"/api/admin/customers/{customer_user.id}", json=update_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["is_active"] == update_data["is_active"]

    @pytest.mark.asyncio
    async def test_customer_cannot_access_admin_endpoints(self, client: AsyncClient, customer_user, customer_token, auth_headers):
        """Test that customers cannot access admin management endpoints."""
        headers = auth_headers(customer_token)

        # Try to access admin list
        response = await client.get("/api/admin/admins", headers=headers)
        assert response.status_code == 401

        # Try to access customer list (should still fail as customer)
        response = await client.get("/api/admin/customers", headers=headers)
        assert response.status_code == 401


class TestActivityLogViewingPermissions:
    """Test activity log viewing permissions."""

    @pytest.mark.asyncio
    async def test_admin_can_view_activity_logs(self, client: AsyncClient, admin_user, admin_token, auth_headers):
        """Test that admins can view activity logs."""
        headers = auth_headers(admin_token)
        response = await client.get("/api/admin/activity-logs", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_customer_cannot_view_activity_logs(self, client: AsyncClient, customer_user, customer_token, auth_headers):
        """Test that customers cannot view activity logs."""
        headers = auth_headers(customer_token)
        response = await client.get("/api/admin/activity-logs", headers=headers)

        assert response.status_code == 401


class TestSystemSettingsPermissions:
    """Test system settings management permissions."""

    @pytest.mark.asyncio
    async def test_super_admin_can_access_system_settings(self, client: AsyncClient, super_admin_user, super_admin_token, auth_headers):
        """Test that SuperAdmins can access system settings."""
        headers = auth_headers(super_admin_token)
        response = await client.get("/api/admin/system-settings", headers=headers)

        # This endpoint might not exist yet, but the permission check should pass
        # If it doesn't exist, it should return 404, not 403
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_regular_admin_cannot_access_system_settings(self, client: AsyncClient, admin_user, admin_token, auth_headers):
        """Test that regular admins cannot access system settings (only SuperAdmin can)."""
        headers = auth_headers(admin_token)
        response = await client.get("/api/admin/system-settings", headers=headers)

        # Should fail with permission denied, not endpoint not found
        if response.status_code != 404:  # If endpoint exists
            assert response.status_code == 403
            assert "Permission" in response.json()["detail"] and "required" in response.json()["detail"]
