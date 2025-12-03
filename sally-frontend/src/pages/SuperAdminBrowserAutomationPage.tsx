import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { browserAutomationService, BrowserTaskRequest, BrowserHealthResponse, AvailableModel } from '../services/browserAutomationService';
import { Globe, Play, Loader2, CheckCircle2, XCircle, AlertCircle, RefreshCw, Info } from 'lucide-react';
import toast from 'react-hot-toast';

const SuperAdminBrowserAutomationPage: React.FC = () => {
  const [task, setTask] = useState('');
  const [url, setUrl] = useState('');
  const [modelName, setModelName] = useState<string>('');
  const [maxSteps, setMaxSteps] = useState(20);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);
  const [health, setHealth] = useState<BrowserHealthResponse | null>(null);
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([]);
  const [isHealthLoading, setIsHealthLoading] = useState(false);
  const [useCurrentBrowser, setUseCurrentBrowser] = useState(false);
  const [cdpUrl, setCdpUrl] = useState('http://127.0.0.1:9222');

  // بارگذاری وضعیت سلامت و مدل‌های موجود در ابتدا
  useEffect(() => {
    loadHealthStatus();
    loadAvailableModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadHealthStatus = async () => {
    setIsHealthLoading(true);
    try {
      const healthData = await browserAutomationService.getHealth();
      setHealth(healthData);
    } catch (err: any) {
      console.error('Failed to load health status:', err);
      toast.error('خطا در بارگذاری وضعیت سلامت');
    } finally {
      setIsHealthLoading(false);
    }
  };

  const loadAvailableModels = async () => {
    try {
      const models = await browserAutomationService.getAvailableModels();
      setAvailableModels(models);
      // انتخاب اولین مدل به صورت پیش‌فرض
      if (models.length > 0 && !modelName) {
        setModelName(models[0].name);
      }
    } catch (err: any) {
      console.error('Failed to load available models:', err);
      toast.error('خطا در بارگذاری مدل‌های موجود');
    }
  };

  const handleExecute = async () => {
    if (!task.trim()) {
      toast.error('لطفاً دستور را وارد کنید');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setExecutionTime(null);

    try {
      const request: BrowserTaskRequest = {
        task: task.trim(),
        ...(url.trim() && { url: url.trim() }),
        ...(modelName && { model_name: modelName }),
        max_steps: maxSteps,
        ...(useCurrentBrowser && { cdp_url: cdpUrl, use_current_page: true }),
      };

      const response = await browserAutomationService.executeTask(request);

      if (response.success) {
        setResult(response.result || 'وظیفه با موفقیت انجام شد');
        setExecutionTime(response.execution_time);
        toast.success('وظیفه با موفقیت انجام شد!');
      } else {
        let errorMsg = response.error || 'خطای نامشخص';
        if (useCurrentBrowser && (errorMsg.includes('CDP') || errorMsg.includes('connect') || errorMsg.includes('browser'))) {
          errorMsg = `خطا در اتصال به مرورگر.\n\nبرای استفاده:\n1. همه Chrome ها را ببندید\n2. این دستور را اجرا کنید:\nchrome.exe --remote-debugging-port=9222 --user-data-dir=C:\\temp\\chrome-debug\n3. به این صفحه برگردید\n\nخطا: ${errorMsg}`;
        }
        setError(errorMsg);
        toast.error('خطا در اجرای وظیفه');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'خطا در اجرای وظیفه';
      let displayMessage = errorMessage;
      if (useCurrentBrowser && (errorMessage.includes('CDP') || errorMessage.includes('connect') || errorMessage.includes('browser'))) {
        displayMessage = `خطا در اتصال به مرورگر.\n\nبرای استفاده:\n1. همه Chrome ها را ببندید\n2. این دستور را اجرا کنید:\nchrome.exe --remote-debugging-port=9222 --user-data-dir=C:\\temp\\chrome-debug\n3. به این صفحه برگردید\n\nخطا: ${errorMessage}`;
      }
      setError(displayMessage);
      toast.error('خطا در اجرای وظیفه');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setTask('');
    setUrl('');
    setResult(null);
    setError(null);
    setExecutionTime(null);
  };

  const exampleTasks = [
    {
      title: 'جستجوی قیمت محصول',
      task: 'Find the price of iPhone 15 on Amazon',
      url: 'https://www.amazon.com',
    },
    {
      title: 'جستجو در YouTube',
      task: 'Search for Python tutorials on YouTube and get top 3 results',
      url: 'https://www.youtube.com',
    },
    {
      title: 'استخراج اخبار',
      task: 'Extract the top 5 news headlines from BBC News homepage',
      url: 'https://www.bbc.com/news',
    },
    {
      title: 'بررسی آب و هوا',
      task: 'Check the weather forecast for Tehran',
      url: 'https://www.google.com',
    },
  ];

  const handleExampleClick = (example: typeof exampleTasks[0]) => {
    setTask(example.task);
    setUrl(example.url);
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Globe className="h-8 w-8 text-blue-600" />
            خودکارسازی مرورگر
          </h1>
          <p className="text-gray-600 mt-2">
            اجرای وظایف مرورگر با استفاده از هوش مصنوعی
          </p>
        </div>
        <Button
          onClick={loadHealthStatus}
          variant="outline"
          size="sm"
          disabled={isHealthLoading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isHealthLoading ? 'animate-spin' : ''}`} />
          بروزرسانی وضعیت
        </Button>
      </div>

      {/* Health Status Card */}
      {health && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="h-5 w-5" />
              وضعیت سیستم
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="flex items-center gap-2">
                <div className={`h-3 w-3 rounded-full ${health.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-sm text-gray-600">وضعیت: {health.status === 'healthy' ? 'سالم' : 'مشکل دارد'}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`h-3 w-3 rounded-full ${health.browser_initialized ? 'bg-green-500' : 'bg-yellow-500'}`} />
                <span className="text-sm text-gray-600">مرورگر: {health.browser_initialized ? 'آماده' : 'آماده نیست'}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`h-3 w-3 rounded-full ${health.llm_initialized ? 'bg-green-500' : 'bg-yellow-500'}`} />
                <span className="text-sm text-gray-600">LLM: {health.llm_initialized ? 'آماده' : 'آماده نیست'}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`h-3 w-3 rounded-full ${health.openrouter_configured ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-sm text-gray-600">OpenRouter: {health.openrouter_configured ? 'پیکربندی شده' : 'پیکربندی نشده'}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Task Input Card */}
          <Card>
            <CardHeader>
              <CardTitle>اجرای وظیفه</CardTitle>
              <CardDescription>
                دستور خود را به صورت طبیعی وارد کنید (مثلاً: "Find iPhone 15 price on Amazon")
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="task">دستور *</Label>
                <Textarea
                  id="task"
                  placeholder="مثلاً: Find the price of iPhone 15 on Amazon"
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  rows={4}
                  className="resize-none"
                  disabled={loading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="url">URL شروع (اختیاری)</Label>
                <Input
                  id="url"
                  type="url"
                  placeholder="https://www.example.com"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={loading}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="model">مدل (اختیاری)</Label>
                  <Select value={modelName} onValueChange={setModelName} disabled={loading}>
                    <SelectTrigger id="model">
                      <SelectValue placeholder="انتخاب مدل" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableModels.map((model) => (
                        <SelectItem key={model.name} value={model.name}>
                          {model.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="maxSteps">حداکثر مراحل</Label>
                  <Input
                    id="maxSteps"
                    type="number"
                    min={1}
                    max={50}
                    value={maxSteps}
                    onChange={(e) => setMaxSteps(parseInt(e.target.value) || 20)}
                    disabled={loading}
                  />
                </div>
              </div>

              {/* CDP Options */}
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="useCurrentBrowser" className="text-sm font-medium">
                      استفاده از مرورگر فعلی (CDP)
                    </Label>
                  </div>
                  <button
                    onClick={() => setUseCurrentBrowser(!useCurrentBrowser)}
                    disabled={loading}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      useCurrentBrowser ? 'bg-green-500' : 'bg-gray-300'
                    } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        useCurrentBrowser ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
                
                {useCurrentBrowser && (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="cdpUrl" className="text-xs">آدرس CDP</Label>
                      <Input
                        id="cdpUrl"
                        type="text"
                        value={cdpUrl}
                        onChange={(e) => setCdpUrl(e.target.value)}
                        placeholder="http://127.0.0.1:9222"
                        disabled={loading}
                        className="text-sm"
                      />
                    </div>
                    <Alert className="border-blue-200 bg-blue-50">
                      <Info className="h-4 w-4 text-blue-600" />
                      <AlertDescription className="text-xs text-blue-800">
                        برای استفاده، ابتدا همه Chrome ها را ببندید، سپس با این دستور باز کنید:
                        <code className="block mt-1 bg-blue-100 px-2 py-1 rounded text-xs whitespace-pre-wrap">
                          chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\temp\chrome-debug
                        </code>
                      </AlertDescription>
                    </Alert>
                  </>
                )}
                
                {!useCurrentBrowser && (
                  <p className="text-xs text-gray-500">
                    🔐 یک مرورگر جدید باز می‌شود و با اطلاعات لاگین پیش‌فرض وارد می‌شود
                  </p>
                )}
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={handleExecute}
                  disabled={loading || !task.trim()}
                  className="flex-1"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      در حال اجرا...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      اجرا
                    </>
                  )}
                </Button>
                <Button
                  onClick={handleClear}
                  variant="outline"
                  disabled={loading}
                >
                  پاک کردن
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Result Card */}
          {(result || error) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {result ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-600" />
                  )}
                  نتیجه
                </CardTitle>
              </CardHeader>
              <CardContent>
                {result && (
                  <div className="space-y-2">
                    <Alert>
                      <CheckCircle2 className="h-4 w-4" />
                      <AlertDescription className="whitespace-pre-wrap">
                        {result}
                      </AlertDescription>
                    </Alert>
                    {executionTime && (
                      <p className="text-sm text-gray-500 mt-2">
                        زمان اجرا: {executionTime.toFixed(2)} ثانیه
                      </p>
                    )}
                  </div>
                )}
                {error && (
                  <Alert className="border-red-200 bg-red-50">
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <AlertDescription className="text-red-800">{error}</AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Examples Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>مثال‌های آماده</CardTitle>
              <CardDescription>
                برای شروع سریع، روی یکی از مثال‌ها کلیک کنید
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {exampleTasks.map((example, index) => (
                <Button
                  key={index}
                  variant="outline"
                  className="w-full text-right justify-start"
                  onClick={() => handleExampleClick(example)}
                  disabled={loading}
                >
                  <div className="text-left">
                    <div className="font-medium">{example.title}</div>
                    <div className="text-xs text-gray-500 truncate">{example.task}</div>
                  </div>
                </Button>
              ))}
            </CardContent>
          </Card>

          {/* Tips Card */}
          <Card>
            <CardHeader>
              <CardTitle>نکات مهم</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-gray-600">
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <p>دستورات را به صورت طبیعی و واضح بنویسید</p>
              </div>
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <p>وظایف ممکن است چند ثانیه تا چند دقیقه طول بکشند</p>
              </div>
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <p>از URLهای مورد اعتماد استفاده کنید</p>
              </div>
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <p>هر درخواست به OpenRouter هزینه دارد</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default SuperAdminBrowserAutomationPage;

