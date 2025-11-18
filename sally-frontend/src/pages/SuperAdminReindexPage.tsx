import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Alert, AlertDescription } from '../components/ui/alert';
import api from '../services/authService';

interface ReindexJob {
  status: string;
  progress: number;
  message: string;
  started_at?: string;
  completed_at?: string;
  details?: {
    total_articles?: number;
    successful?: number;
    failed?: number;
    total_chunks?: number;
  };
}

const SuperAdminReindexPage: React.FC = () => {
  const [mode, setMode] = useState<'all' | 'single' | 'multiple'>('single');
  const [articleId, setArticleId] = useState('');
  const [articleTitle, setArticleTitle] = useState('');
  const [articleIds, setArticleIds] = useState('');
  const [articleTitles, setArticleTitles] = useState('');
  const [removeOld, setRemoveOld] = useState(true);
  const [clearAllFirst, setClearAllFirst] = useState(false);
  const [loading, setLoading] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<ReindexJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [debugInfo, setDebugInfo] = useState<any>(null);

  // Poll job status
  useEffect(() => {
    if (!currentJobId) return;

    const interval = setInterval(async () => {
      try {
        const response = await api.get(`/api/super-admin/reindex/status/${currentJobId}`);
        setJobStatus(response.data);

        if (response.data.status === 'completed' || response.data.status === 'failed') {
          setCurrentJobId(null);
          setLoading(false);
          
          if (response.data.status === 'completed') {
            setSuccess(response.data.message);
          } else {
            setError(response.data.message);
          }
        }
      } catch (err) {
        console.error('Error polling job status:', err);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [currentJobId]);

  const handleDebug = async () => {
    try {
      setError(null);
      const response = await api.get('/api/super-admin/reindex/debug');
      setDebugInfo(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در دریافت اطلاعات debug');
    }
  };

  const handleReindex = async () => {
    setError(null);
    setSuccess(null);
    setLoading(true);
    setJobStatus(null);
    setDebugInfo(null);

    try {
      const payload: any = {
        mode,
        remove_old: removeOld,
        clear_all_first: clearAllFirst
      };

      if (mode === 'single') {
        if (articleId) payload.article_id = articleId;
        if (articleTitle) payload.article_title = articleTitle;

        if (!articleId && !articleTitle) {
          setError('لطفاً حداقل Article ID یا عنوان مقاله را وارد کنید');
          setLoading(false);
          return;
        }
      } else if (mode === 'multiple') {
        if (articleIds) {
          payload.article_ids = articleIds.split(',').map(id => id.trim()).filter(id => id);
        }
        if (articleTitles) {
          payload.article_titles = articleTitles.split(',').map(title => title.trim()).filter(title => title);
        }

        if (!payload.article_ids && !payload.article_titles) {
          setError('لطفاً حداقل یک Article ID یا عنوان وارد کنید');
          setLoading(false);
          return;
        }
      }

      const response = await api.post('/api/super-admin/reindex', payload);
      setCurrentJobId(response.data.task_id);
      setSuccess('عملیات Re-indexing شروع شد...');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در شروع عملیات');
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <h1 className="text-3xl font-bold mb-6">🔄 Re-indexing پایگاه دانش</h1>

      {/* Alert Messages */}
      {error && (
        <Alert className="mb-4 bg-red-50 border-red-200">
          <AlertDescription className="text-red-800">{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="mb-4 bg-green-50 border-green-200">
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      {/* Job Status */}
      {jobStatus && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>وضعیت عملیات</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="font-semibold">پیشرفت</span>
                  <span>{jobStatus.progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div
                    className={`h-4 rounded-full transition-all ${
                      jobStatus.status === 'completed' ? 'bg-green-600' :
                      jobStatus.status === 'failed' ? 'bg-red-600' :
                      'bg-blue-600'
                    }`}
                    style={{ width: `${jobStatus.progress}%` }}
                  />
                </div>
              </div>

              <div>
                <span className="font-semibold">وضعیت: </span>
                <span className={`px-2 py-1 rounded ${
                  jobStatus.status === 'running' ? 'bg-blue-100 text-blue-800' :
                  jobStatus.status === 'completed' ? 'bg-green-100 text-green-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {jobStatus.status}
                </span>
              </div>

              <div>
                <span className="font-semibold">پیام: </span>
                <span>{jobStatus.message}</span>
              </div>

              {jobStatus.details && (
                <div className="mt-4 p-4 bg-gray-50 rounded">
                  <h4 className="font-semibold mb-2">جزئیات:</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {jobStatus.details.total_articles && (
                      <div>کل مقالات: {jobStatus.details.total_articles}</div>
                    )}
                    {jobStatus.details.successful !== undefined && (
                      <div className="text-green-600">موفق: {jobStatus.details.successful}</div>
                    )}
                    {jobStatus.details.failed !== undefined && (
                      <div className="text-red-600">ناموفق: {jobStatus.details.failed}</div>
                    )}
                    {jobStatus.details.total_chunks && (
                      <div>کل Chunks: {jobStatus.details.total_chunks}</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>تنظیمات Re-indexing</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Mode Selection */}
            <div>
              <label className="block text-sm font-semibold mb-2">نوع عملیات</label>
              <div className="flex gap-4">
                <button
                  onClick={() => setMode('all')}
                  className={`px-4 py-2 rounded ${
                    mode === 'all'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700'
                  }`}
                >
                  همه مقالات
                </button>
                <button
                  onClick={() => setMode('single')}
                  className={`px-4 py-2 rounded ${
                    mode === 'single'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700'
                  }`}
                >
                  یک مقاله
                </button>
                <button
                  onClick={() => setMode('multiple')}
                  className={`px-4 py-2 rounded ${
                    mode === 'multiple'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700'
                  }`}
                >
                  چند مقاله
                </button>
              </div>
            </div>

            {/* Single Mode Fields */}
            {mode === 'single' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold mb-2">Article ID</label>
                  <input
                    type="text"
                    value={articleId}
                    onChange={(e) => setArticleId(e.target.value)}
                    placeholder="مثال: 507f1f77bcf86cd799439011"
                    className="w-full p-2 border rounded"
                  />
                </div>
                <div className="text-center text-gray-500">یا</div>
                <div>
                  <label className="block text-sm font-semibold mb-2">عنوان مقاله</label>
                  <input
                    type="text"
                    value={articleTitle}
                    onChange={(e) => setArticleTitle(e.target.value)}
                    placeholder="بخشی از عنوان مقاله"
                    className="w-full p-2 border rounded"
                  />
                </div>
              </div>
            )}

            {/* Multiple Mode Fields */}
            {mode === 'multiple' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold mb-2">
                    Article IDs (با کاما جدا شوند)
                  </label>
                  <textarea
                    value={articleIds}
                    onChange={(e) => setArticleIds(e.target.value)}
                    placeholder="id1, id2, id3"
                    rows={3}
                    className="w-full p-2 border rounded"
                  />
                </div>
                <div className="text-center text-gray-500">یا</div>
                <div>
                  <label className="block text-sm font-semibold mb-2">
                    عناوین مقالات (با کاما جدا شوند)
                  </label>
                  <textarea
                    value={articleTitles}
                    onChange={(e) => setArticleTitles(e.target.value)}
                    placeholder="عنوان1, عنوان2, عنوان3"
                    rows={3}
                    className="w-full p-2 border rounded"
                  />
                </div>
              </div>
            )}

            {/* Options */}
            <div className="space-y-3 pt-4 border-t">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="removeOld"
                  checked={removeOld}
                  onChange={(e) => setRemoveOld(e.target.checked)}
                  className="w-4 h-4"
                />
                <label htmlFor="removeOld" className="text-sm">
                  حذف Chunks قبلی مقالات
                </label>
              </div>

              {mode === 'all' && (
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="clearAll"
                    checked={clearAllFirst}
                    onChange={(e) => setClearAllFirst(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="clearAll" className="text-sm font-semibold text-red-600">
                    ⚠️ پاکسازی کامل Weaviate قبل از شروع (خطرناک!)
                  </label>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <Button
              onClick={handleReindex}
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white"
            >
              {loading ? '🔄 در حال پردازش...' : '🚀 شروع Re-indexing'}
            </Button>

            {/* Warning */}
            {mode === 'all' && clearAllFirst && (
              <Alert className="bg-yellow-50 border-yellow-200">
                <AlertDescription className="text-yellow-800">
                  ⚠️ هشدار: این عملیات تمام داده‌های Weaviate را پاک می‌کند!
                  مطمئن شوید که از MongoDB backup دارید.
                </AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Debug Information */}
      {debugInfo && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>🔍 اطلاعات Debug</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 text-sm">
              {/* MongoDB Info */}
              <div className="p-4 bg-blue-50 rounded">
                <h4 className="font-semibold mb-2">📊 MongoDB</h4>
                <div className="space-y-1">
                  <div>کل مقالات: {debugInfo.mongodb.total_articles}</div>
                  <div>مقالات منتشر شده: {debugInfo.mongodb.published_articles}</div>
                  {debugInfo.mongodb.sample_articles.length > 0 && (
                    <div className="mt-2">
                      <div className="font-semibold">نمونه مقالات:</div>
                      {debugInfo.mongodb.sample_articles.map((article: any, idx: number) => (
                        <div key={idx} className="ml-4 text-xs">
                          • {article.title} (طول: {article.content_length} کاراکتر)
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Weaviate Info */}
              <div className={`p-4 rounded ${debugInfo.weaviate.error ? 'bg-red-50' : 'bg-green-50'}`}>
                <h4 className="font-semibold mb-2">🔷 Weaviate</h4>
                <div className="space-y-1">
                  <div>تعداد Chunks: {debugInfo.weaviate.total_chunks}</div>
                  {debugInfo.weaviate.error && (
                    <div className="text-red-600">خطا: {debugInfo.weaviate.error}</div>
                  )}
                </div>
              </div>

              {/* Embedder Config */}
              <div className="p-4 bg-purple-50 rounded">
                <h4 className="font-semibold mb-2">⚙️ تنظیمات Embedder</h4>
                <div className="space-y-1">
                  <div>مدل: {debugInfo.embedder_config.model}</div>
                  <div>API Key: {debugInfo.embedder_config.api_key_set ? '✅ تنظیم شده' : '❌ تنظیم نشده'}</div>
                  <div>Base URL: {debugInfo.embedder_config.base_url || 'پیش‌فرض'}</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Documentation */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>📚 راهنما</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-2 text-gray-700">
          <p><strong>همه مقالات:</strong> تمام مقالات منتشر شده را مجدداً ایندکس می‌کند</p>
          <p><strong>یک مقاله:</strong> فقط یک مقاله را با ID یا عنوان ایندکس می‌کند</p>
          <p><strong>چند مقاله:</strong> چند مقاله را به صورت همزمان ایندکس می‌کند</p>
          <p className="pt-2 border-t"><strong>💡 نکته:</strong> عملیات در پس‌زمینه اجرا می‌شود و می‌توانید پیشرفت آن را مشاهده کنید</p>
          <Button
            onClick={handleDebug}
            variant="outline"
            className="mt-4 w-full"
          >
            🔍 بررسی وضعیت سیستم (Debug)
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

export default SuperAdminReindexPage;

