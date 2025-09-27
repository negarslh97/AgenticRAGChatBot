"""
Tests for authentication module (Registration, Login, Token validation).
"""
import pytest
from httpx import AsyncClient
from app.core.security import verify_password


class TestCustomerRegistration:
    """Test customer registration functionality."""

    @pytest.mark.asyncio
    async def test_customer_registration_success(self, client: AsyncClient, faker):
        """Test successful customer registration."""
        customer_data = {
            "email": faker.email(),
            "password": "testpassword123",
            "full_name": faker.name()
        }

        response = await client.post("/api/auth/register/customer", json=customer_data)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == customer_data["email"]
        assert data["full_name"] == customer_data["full_name"]
        assert data["is_active"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_customer_registration_duplicate_email(self, client: AsyncClient, faker):
        """Test registration fails with duplicate email."""
        customer_data = {
            "email": faker.email(),
            "password": "testpassword123",
            "full_name": faker.name()
        }

        # First registration should succeed
        response1 = await client.post("/api/auth/register/customer", json=customer_data)
        assert response1.status_code == 200

        # Second registration with same email should fail
        response2 = await client.post("/api/auth/register/customer", json=customer_data)
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"]

    @pytest.mark.asyncio
    async def test_customer_registration_invalid_email(self, client: AsyncClient, faker):
        """Test registration fails with invalid email format."""
        customer_data = {
            "email": "invalid-email-format",
            "password": "testpassword123",
            "full_name": faker.name()
        }

        response = await client.post("/api/auth/register/customer", json=customer_data)
        assert response.status_code == 422  # Validation error


class TestAdminRegistration:
    """Test admin registration functionality."""

    @pytest.mark.asyncio
    async def test_admin_registration_by_super_admin(self, client: AsyncClient, faker, super_admin_token, auth_headers):
        """Test admin registration by super admin succeeds."""
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
        response = await client.post("/api/auth/register/admin", json=admin_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == admin_data["email"]
        assert data["full_name"] == admin_data["full_name"]
        assert data["role"] == "Admin"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_admin_registration_by_regular_admin_fails(self, client: AsyncClient, faker, admin_token, auth_headers):
        """Test admin registration by regular admin fails."""
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
        response = await client.post("/api/auth/register/admin", json=admin_data, headers=headers)

        assert response.status_code == 403
        assert "Permission denied" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_registration_duplicate_email(self, client: AsyncClient, faker, super_admin_token, auth_headers):
        """Test admin registration fails with duplicate email."""
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

        # First registration should succeed
        response1 = await client.post("/api/auth/register/admin", json=admin_data, headers=headers)
        assert response1.status_code == 201

        # Second registration should fail
        response2 = await client.post("/api/auth/register/admin", json=admin_data, headers=headers)
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"]


class TestLogin:
    """Test login functionality for all user types."""

    @pytest.mark.asyncio
    async def test_customer_login_success(self, client: AsyncClient, customer_user):
        """Test successful customer login."""
        login_data = {
            "username": customer_user.email,  # OAuth2PasswordRequestForm uses 'username' field
            "password": "testpassword123"
        }

        response = await client.post("/api/auth/login", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert data["user_type"] == "customer"
        assert data["user"]["email"] == customer_user.email
        assert data["user"]["full_name"] == customer_user.full_name

    @pytest.mark.asyncio
    async def test_admin_login_success(self, client: AsyncClient, admin_user):
        """Test successful admin login."""
        login_data = {
            "username": admin_user.email,
            "password": "testpassword123"
        }

        response = await client.post("/api/auth/login", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user_type"] in ["Admin", "SuperAdmin"]
        assert data["user"]["email"] == admin_user.email
        assert data["user"]["full_name"] == admin_user.full_name
        assert data["user"]["role"] == admin_user.role_name

    @pytest.mark.asyncio
    async def test_super_admin_login_success(self, client: AsyncClient, super_admin_user):
        """Test successful super admin login."""
        login_data = {
            "username": super_admin_user.email,
            "password": "testpassword123"
        }

        response = await client.post("/api/auth/login", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user_type"] == "SuperAdmin"
        assert data["user"]["email"] == super_admin_user.email
        assert data["user"]["role"] == "SuperAdmin"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, customer_user):
        """Test login fails with wrong password."""
        login_data = {
            "username": customer_user.email,
            "password": "wrongpassword"
        }

        response = await client.post("/api/auth/login", data=login_data)

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, customer_user):
        """Test login fails for inactive user."""
        # Deactivate user
        customer_user.is_active = False
        await customer_user.save()

        login_data = {
            "username": customer_user.email,
            "password": "testpassword123"
        }

        response = await client.post("/api/auth/login", data=login_data)

        assert response.status_code == 400
        assert "Inactive customer account" in response.json()["detail"]


class TestTokenValidation:
    """Test JWT token structure and validation."""

    @pytest.mark.asyncio
    async def test_token_contains_correct_user_info(self, client: AsyncClient, customer_user, customer_token, auth_headers):
        """Test that JWT token contains correct user information."""
        from app.core.security import create_access_token
        from datetime import timedelta
        from jose import jwt

        # Verify token structure by decoding it
        headers = auth_headers(customer_token)

        # Get user info from /me endpoint
        response = await client.get("/api/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["user_type"] == "customer"
        assert data["user"]["id"] == str(customer_user.id)
        assert data["user"]["email"] == customer_user.email
        assert data["user"]["full_name"] == customer_user.full_name
        assert data["user"]["role"] == "Customer"

    @pytest.mark.asyncio
    async def test_admin_token_contains_correct_info(self, client: AsyncClient, admin_user, admin_token, auth_headers):
        """Test that admin JWT token contains correct information."""
        headers = auth_headers(admin_token)

        # Get user info from /me endpoint
        response = await client.get("/api/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["user_type"] in ["Admin", "SuperAdmin"]
        assert data["user"]["id"] == str(admin_user.id)
        assert data["user"]["email"] == admin_user.email
        assert data["user"]["role"] == admin_user.role_name

    @pytest.mark.asyncio
    async def test_super_admin_token_contains_correct_info(self, client: AsyncClient, super_admin_user, super_admin_token, auth_headers):
        """Test that super admin JWT token contains correct information."""
        headers = auth_headers(super_admin_token)

        # Get user info from /me endpoint
        response = await client.get("/api/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["user_type"] == "SuperAdmin"
        assert data["user"]["id"] == str(super_admin_user.id)
        assert data["user"]["email"] == super_admin_user.email
        assert data["user"]["role"] == "SuperAdmin"

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, client: AsyncClient, auth_headers):
        """Test that invalid tokens are rejected."""
        headers = auth_headers("invalid.jwt.token")

        response = await client.get("/api/auth/me", headers=headers)

        assert response.status_code == 401
        assert "Invalid authentication credentials" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_missing_token_rejected(self, client: AsyncClient):
        """Test that missing authorization header is rejected."""
        response = await client.get("/api/auth/me")

        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]


class TestTokenRefresh:
    """Test token refresh functionality."""

    @pytest.mark.asyncio
    async def test_customer_token_refresh(self, client: AsyncClient, customer_user, customer_token, auth_headers):
        """Test customer token refresh."""
        headers = auth_headers(customer_token)

        response = await client.post("/api/auth/refresh", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_type"] == "customer"
        assert data["user"]["id"] == str(customer_user.id)

    @pytest.mark.asyncio
    async def test_admin_token_refresh(self, client: AsyncClient, admin_user, admin_token, auth_headers):
        """Test admin token refresh."""
        headers = auth_headers(admin_token)

        response = await client.post("/api/auth/refresh", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_type"] in ["Admin", "SuperAdmin"]
        assert data["user"]["id"] == str(admin_user.id)

    @pytest.mark.asyncio
    async def test_token_refresh_without_auth(self, client: AsyncClient):
        """Test token refresh fails without authentication."""
        response = await client.post("/api/auth/refresh")

        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
