/**
 * صفحه مدیریت دسته‌بندی‌های Knowledge Base
 * 
 * قابلیت‌ها:
 * - نمایش لیست دسته‌بندی‌ها
 * - افزودن دسته‌بندی جدید
 * - ویرایش دسته‌بندی
 * - حذف دسته‌بندی (با گزینه cascade)
 * - نمایش درخت سلسله‌مراتبی
 */

import React, { useState, useEffect } from 'react';
import categoryService, { Category, CategoryCreate, CategoryUpdate } from '../services/categoryService';
import './SuperAdminCategoriesPage.css';

const SuperAdminCategoriesPage: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [currentCategory, setCurrentCategory] = useState<Category | null>(null);
  
  // Form state
  const [formData, setFormData] = useState<CategoryCreate>({
    name: '',
    slug: '',
    description: '',
    parent_id: null,
    is_public: true
  });

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await categoryService.getCategories();
      setCategories(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در دریافت دسته‌بندی‌ها');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (mode: 'create' | 'edit', category?: Category) => {
    setModalMode(mode);
    
    if (mode === 'edit' && category) {
      setCurrentCategory(category);
      setFormData({
        name: category.name,
        slug: category.slug,
        description: category.description || '',
        parent_id: category.parent_id || null,
        is_public: category.is_public
      });
    } else {
      setCurrentCategory(null);
      setFormData({
        name: '',
        slug: '',
        description: '',
        parent_id: null,
        is_public: true
      });
    }
    
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setCurrentCategory(null);
    setError(null);
    setSuccess(null);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    }));
    
    // Auto-generate slug from name
    if (name === 'name' && modalMode === 'create') {
      setFormData(prev => ({
        ...prev,
        slug: categoryService.generateSlug(value)
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      if (modalMode === 'create') {
        await categoryService.createCategory(formData);
        setSuccess('✅ دسته‌بندی با موفقیت ایجاد شد');
      } else if (currentCategory) {
        await categoryService.updateCategory(currentCategory.id, formData as CategoryUpdate);
        setSuccess('✅ دسته‌بندی با موفقیت به‌روزرسانی شد');
      }
      
      await loadCategories();
      setTimeout(() => {
        handleCloseModal();
        setSuccess(null);
      }, 1500);
      
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در ذخیره دسته‌بندی');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (categoryId: string, categoryName: string) => {
    if (!window.confirm(`آیا از حذف دسته‌بندی "${categoryName}" اطمینان دارید؟\n\n⚠️ زیردسته‌ها به والد منتقل می‌شوند و دسته‌بندی از مقالات حذف می‌شود.`)) {
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await categoryService.deleteCategory(categoryId, false, true);
      setSuccess(`✅ ${result.message}`);
      await loadCategories();
      
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در حذف دسته‌بندی');
    } finally {
      setLoading(false);
    }
  };

  // پیدا کردن نام دسته‌بندی والد
  const getParentName = (parentId: string | null | undefined) => {
    if (!parentId) return '-';
    const parent = categories.find(c => c.id === parentId);
    return parent ? parent.name : 'نامشخص';
  };

  return (
    <div className="categories-page">
      <div className="page-header">
        <h1>مدیریت دسته‌بندی‌ها</h1>
        <button className="btn-primary" onClick={() => handleOpenModal('create')}>
          ➕ دسته‌بندی جدید
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {loading && !showModal ? (
        <div className="loading">در حال بارگذاری...</div>
      ) : (
        <div className="categories-table-container">
          <table className="categories-table">
            <thead>
              <tr>
                <th>نام دسته‌بندی</th>
                <th>Slug</th>
                <th>دسته‌بندی والد</th>
                <th>وضعیت</th>
                <th>تعداد مقالات</th>
                <th>تعداد زیردسته</th>
                <th>عملیات</th>
              </tr>
            </thead>
            <tbody>
              {categories.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center">
                    هیچ دسته‌بندی‌ای یافت نشد
                  </td>
                </tr>
              ) : (
                categories.map(category => (
                  <tr key={category.id}>
                    <td>
                      <strong>{category.name}</strong>
                      {category.description && (
                        <small className="text-muted d-block">{category.description}</small>
                      )}
                    </td>
                    <td><code>{category.slug}</code></td>
                    <td>{getParentName(category.parent_id)}</td>
                    <td>
                      <span className={`badge ${category.is_public ? 'badge-success' : 'badge-warning'}`}>
                        {category.is_public ? '🌐 عمومی' : '🔒 خصوصی'}
                      </span>
                    </td>
                    <td className="text-center">{category.articles_count || 0}</td>
                    <td className="text-center">{category.children_count || 0}</td>
                    <td>
                      <div className="btn-group">
                        <button
                          className="btn-sm btn-secondary"
                          onClick={() => handleOpenModal('edit', category)}
                          title="ویرایش"
                        >
                          ✏️
                        </button>
                        <button
                          className="btn-sm btn-danger"
                          onClick={() => handleDelete(category.id, category.name)}
                          title="حذف"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal for Create/Edit */}
      {showModal && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{modalMode === 'create' ? '➕ دسته‌بندی جدید' : '✏️ ویرایش دسته‌بندی'}</h2>
              <button className="btn-close" onClick={handleCloseModal}>✖</button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {error && <div className="alert alert-error">{error}</div>}
                {success && <div className="alert alert-success">{success}</div>}

                <div className="form-group">
                  <label htmlFor="name">نام دسته‌بندی *</label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                    placeholder="مثال: آموزش محصول"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="slug">Slug *</label>
                  <input
                    type="text"
                    id="slug"
                    name="slug"
                    value={formData.slug}
                    onChange={handleInputChange}
                    required
                    placeholder="product-tutorial"
                    disabled={modalMode === 'create'}
                  />
                  <small>به صورت خودکار از نام ساخته می‌شود</small>
                </div>

                <div className="form-group">
                  <label htmlFor="description">توضیحات</label>
                  <textarea
                    id="description"
                    name="description"
                    value={formData.description}
                    onChange={handleInputChange}
                    rows={3}
                    placeholder="توضیحات کوتاه درباره این دسته‌بندی..."
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="parent_id">دسته‌بندی والد</label>
                  <select
                    id="parent_id"
                    name="parent_id"
                    value={formData.parent_id || ''}
                    onChange={handleInputChange}
                  >
                    <option value="">بدون والد (Root)</option>
                    {categories
                      .filter(c => modalMode === 'edit' ? c.id !== currentCategory?.id : true)
                      .map(c => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="form-group form-check">
                  <input
                    type="checkbox"
                    id="is_public"
                    name="is_public"
                    checked={formData.is_public}
                    onChange={handleInputChange}
                  />
                  <label htmlFor="is_public">
                    عمومی (قابل مشاهده برای همه کاربران)
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={handleCloseModal}>
                  انصراف
                </button>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? 'در حال ذخیره...' : modalMode === 'create' ? '✅ ایجاد' : '💾 ذخیره'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SuperAdminCategoriesPage;
