"""
Tests for knowledge base functionality.
"""
import pytest
from httpx import AsyncClient
from app.domain.entities_refactored import ArticleStatus, ArticleVisibility


class TestPublicKnowledgeBaseAccess:
    """Test public (guest) access to knowledge base."""

    @pytest.mark.asyncio
    async def test_guest_can_view_public_articles(self, client: AsyncClient, test_article):
        """Test that guests can view published public articles."""
        # Update article to be published and public
        test_article.status = ArticleStatus.PUBLISHED
        test_article.visibility = ArticleVisibility.PUBLIC
        await test_article.save()

        response = await client.get("/api/kb/articles")

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Verify our test article is in the results
        article_ids = [article["id"] for article in data]
        assert str(test_article.id) in article_ids

    @pytest.mark.asyncio
    async def test_guest_cannot_view_customer_articles(self, client: AsyncClient, test_article):
        """Test that guests cannot view customer-only articles."""
        # Update article to be published but customer-only
        test_article.status = ArticleStatus.PUBLISHED
        test_article.visibility = ArticleVisibility.CUSTOMER
        await test_article.save()

        response = await client.get("/api/kb/articles")

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)

        # Test article should not be in public results
        article_ids = [article["id"] for article in data]
        assert str(test_article.id) not in article_ids

    @pytest.mark.asyncio
    async def test_guest_cannot_view_draft_articles(self, client: AsyncClient, test_article):
        """Test that guests cannot view draft articles."""
        # Update article to be draft and public
        test_article.status = ArticleStatus.DRAFT
        test_article.visibility = ArticleVisibility.PUBLIC
        await test_article.save()

        response = await client.get("/api/kb/articles")

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)

        # Draft article should not be visible
        article_ids = [article["id"] for article in data]
        assert str(test_article.id) not in article_ids

    @pytest.mark.asyncio
    async def test_guest_can_view_categories(self, client: AsyncClient, test_category):
        """Test that guests can view public categories."""
        response = await client.get("/api/kb/categories")

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)

        # Our test category should be in the results
        category_ids = [category["id"] for category in data]
        assert str(test_category.id) in category_ids

    @pytest.mark.asyncio
    async def test_guest_can_search_articles(self, client: AsyncClient, test_article):
        """Test that guests can search public articles."""
        # Make article published and public
        test_article.status = ArticleStatus.PUBLISHED
        test_article.visibility = ArticleVisibility.PUBLIC
        await test_article.save()

        # Search for a word from the title
        search_term = test_article.title.split()[0]  # First word of title
        response = await client.get(f"/api/kb/search?q={search_term}")

        assert response.status_code == 201
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

        # Should find our article
        result_ids = [result["id"] for result in data["results"]]
        assert str(test_article.id) in result_ids


class TestCustomerKnowledgeBaseAccess:
    """Test authenticated customer access to knowledge base."""

    @pytest.mark.asyncio
    async def test_customer_can_view_public_articles(self, client: AsyncClient, customer_token, auth_headers, test_article):
        """Test that customers can view public articles."""
        # Update article to be published and public
        test_article.status = ArticleStatus.PUBLISHED
        test_article.visibility = ArticleVisibility.PUBLIC
        await test_article.save()

        headers = auth_headers(customer_token)
        response = await client.get("/api/kb/customer/articles", headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)

        # Test article should be in results
        article_ids = [article["id"] for article in data]
        assert str(test_article.id) in article_ids

    @pytest.mark.asyncio
    async def test_customer_can_view_customer_articles(self, client: AsyncClient, customer_token, auth_headers, test_article):
        """Test that customers can view customer-only articles."""
        # Update article to be published and customer-only
        test_article.status = ArticleStatus.PUBLISHED
        test_article.visibility = ArticleVisibility.CUSTOMER
        await test_article.save()

        headers = auth_headers(customer_token)
        response = await client.get("/api/kb/customer/articles", headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)

        # Test article should be in results
        article_ids = [article["id"] for article in data]
        assert str(test_article.id) in article_ids

    @pytest.mark.asyncio
    async def test_customer_cannot_view_internal_articles(self, client: AsyncClient, customer_token, auth_headers, test_article):
        """Test that customers cannot view internal articles."""
        # Update article to be published but internal
        test_article.status = ArticleStatus.PUBLISHED
        test_article.visibility = ArticleVisibility.INTERNAL
        await test_article.save()

        headers = auth_headers(customer_token)
        response = await client.get("/api/kb/customer/articles", headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)

        # Internal article should not be visible to customers
        article_ids = [article["id"] for article in data]
        assert str(test_article.id) not in article_ids


class TestAdminKnowledgeBaseManagement:
    """Test admin knowledge base management functionality."""

    @pytest.mark.asyncio
    async def test_admin_can_create_draft_article(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_category, faker):
        """Test that admins can create draft articles."""
        article_data = {
            "title": faker.sentence(),
            "content_markdown": faker.paragraph(),
            "summary": faker.sentence(),
            "category_id": str(test_category.id),
            "tag_names": ["test", "draft"],
            "status": "draft",
            "visibility": "internal"
        }

        headers = auth_headers(admin_token)
        response = await client.post("/api/super-admin/kb/articles", json=article_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == article_data["title"]
        assert data["status"] == "draft"
        assert data["visibility"] == "internal"
        assert data["author_id"] == str(admin_user.id)

    @pytest.mark.asyncio
    async def test_regular_admin_cannot_publish_articles(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_category, faker):
        """Test that regular admins cannot publish articles (only SuperAdmin can)."""
        article_data = {
            "title": faker.sentence(),
            "content_markdown": faker.paragraph(),
            "summary": faker.sentence(),
            "category_id": str(test_category.id),
            "tag_names": ["test", "published"],
            "status": "published",
            "visibility": "public"
        }

        headers = auth_headers(admin_token)
        response = await client.post("/api/super-admin/kb/articles", json=article_data, headers=headers)

        # Regular admin should not have permission to access SuperAdmin endpoints
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_super_admin_can_publish_articles(self, client: AsyncClient, super_admin_user, super_admin_token, auth_headers, test_category, faker):
        """Test that SuperAdmins can publish articles."""
        article_data = {
            "title": faker.sentence(),
            "content_markdown": faker.paragraph(),
            "summary": faker.sentence(),
            "category_id": str(test_category.id),
            "tag_names": ["test", "published"],
            "status": "published",
            "visibility": "public"
        }

        headers = auth_headers(super_admin_token)
        response = await client.post("/api/super-admin/kb/articles", json=article_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == article_data["title"]
        assert data["status"] == "published"
        assert data["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_super_admin_can_delete_articles(self, client: AsyncClient, super_admin_user, super_admin_token, auth_headers, test_article):
        """Test that SuperAdmins can delete articles."""
        headers = auth_headers(super_admin_token)

        # First verify the article exists
        get_response = await client.get(f"/api/super-admin/kb/articles/{test_article.id}", headers=headers)
        assert get_response.status_code == 200

        # Delete the article
        delete_response = await client.delete(f"/api/super-admin/kb/articles/{test_article.id}", headers=headers)
        assert delete_response.status_code == 204

        # Verify article is deleted
        get_after_delete = await client.get(f"/api/super-admin/kb/articles/{test_article.id}", headers=headers)
        assert get_after_delete.status_code == 404

    @pytest.mark.asyncio
    async def test_regular_admin_cannot_delete_articles(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_article):
        """Test that regular admins cannot delete articles."""
        headers = auth_headers(admin_token)

        # Try to delete the article
        delete_response = await client.delete(f"/api/super-admin/kb/articles/{test_article.id}", headers=headers)

        # Should fail because regular admin doesn't have access to SuperAdmin endpoints
        assert delete_response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_can_update_articles(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_article, faker):
        """Test that admins can update articles they created."""
        update_data = {
            "title": faker.sentence(),
            "content_markdown": faker.paragraph(),
            "summary": faker.sentence(),
            "status": "draft",
            "visibility": "internal"
        }

        headers = auth_headers(admin_token)
        response = await client.put(f"/api/super-admin/kb/articles/{test_article.id}", json=update_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["status"] == "draft"
        assert data["visibility"] == "internal"

    @pytest.mark.asyncio
    async def test_admin_can_view_all_articles(self, client: AsyncClient, admin_user, admin_token, auth_headers, test_article):
        """Test that admins can view all articles including drafts."""
        headers = auth_headers(admin_token)
        response = await client.get("/api/super-admin/kb/articles", headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)

        # Should include our test article
        article_ids = [article["id"] for article in data]
        assert str(test_article.id) in article_ids

    @pytest.mark.asyncio
    async def test_customer_cannot_access_admin_kb_endpoints(self, client: AsyncClient, customer_user, customer_token, auth_headers):
        """Test that customers cannot access admin knowledge base endpoints."""
        headers = auth_headers(customer_token)
        response = await client.get("/api/super-admin/kb/articles", headers=headers)

        assert response.status_code == 401
