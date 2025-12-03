import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, X, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { browserAutomationService } from '../services/browserAutomationService';
import toast from 'react-hot-toast';
import blackCatImage from '../assets/Black-Cat.png';

interface SallyFloatingAgentProps {
  className?: string;
}

const SallyFloatingAgent: React.FC<SallyFloatingAgentProps> = ({ className }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [command, setCommand] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [showResult, setShowResult] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Focus input when expanded
  useEffect(() => {
    if (isExpanded && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isExpanded]);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node) &&
        !command.trim() &&
        !isExecuting
      ) {
        setIsExpanded(false);
        setShowResult(false);
      }
    };

    if (isExpanded) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isExpanded, command, isExecuting]);

  const handleToggle = () => {
    if (!isExpanded) {
      setIsExpanded(true);
      setResult(null);
      setShowResult(false);
    } else {
      if (!command.trim() && !isExecuting) {
        setIsExpanded(false);
        setShowResult(false);
      }
    }
  };

  const handleExecute = async () => {
    if (!command.trim()) {
      toast.error('لطفاً دستور خود را وارد کنید');
      return;
    }

    setIsExecuting(true);
    setResult(null);
    setShowResult(false);

    try {
      // Agent یک browser جدید باز می‌کند و خودش لاگین می‌کند
      // این روش پایدارتر از CDP connection است
      const response = await browserAutomationService.executeAgentCommand({
        task: command.trim(),
        max_steps: 30,
        url: "http://localhost:3000/super-admin", // URL پنل ادمین
        // بدون CDP - agent خودش browser جدید باز می‌کند و لاگین می‌کند
      });

      if (response.success) {
        setResult(response.result || 'وظیفه با موفقیت انجام شد');
        setShowResult(true);
        toast.success('وظیفه با موفقیت انجام شد!');
        // Clear input after success
        setTimeout(() => {
          setCommand('');
          setIsExpanded(false);
          setShowResult(false);
        }, 5000);
      } else {
        setResult(`خطا: ${response.error || 'خطای نامشخص'}`);
        setShowResult(true);
        toast.error('خطا در اجرای وظیفه');
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'خطا در اجرای وظیفه';
      setResult(`خطا: ${errorMessage}`);
      setShowResult(true);
      toast.error('خطا در اجرای وظیفه');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isExecuting && command.trim()) {
        handleExecute();
      }
    }
    if (e.key === 'Escape') {
      if (!isExecuting) {
        setIsExpanded(false);
        setCommand('');
        setShowResult(false);
      }
    }
  };

  const handleCloseResult = () => {
    setShowResult(false);
    setResult(null);
  };

  return (
    <div
      ref={containerRef}
      className={`fixed bottom-6 left-6 z-50 transition-all duration-300 ${className}`}
    >
      {/* Collapsed State - Button */}
      {!isExpanded && (
        <button
          onClick={handleToggle}
          className="w-14 h-14 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 shadow-lg hover:shadow-xl transform hover:scale-110 transition-all duration-300 flex items-center justify-center group relative overflow-hidden"
          aria-label="دستیار سالی"
          title="دستیار هوشمند سالی - کلیک کنید"
        >
          <img
            src={blackCatImage}
            alt="سالی"
            className="w-12 h-12 rounded-full object-cover border-2 border-white shadow-md group-hover:border-purple-300 transition-all z-10 relative"
          />
          {/* Pulse animation */}
          <span className="absolute inset-0 rounded-full bg-purple-400 animate-ping opacity-75"></span>
          {/* Sparkle icon */}
          <Sparkles className="absolute -top-1 -right-1 w-5 h-5 text-yellow-300 animate-pulse z-10" />
        </button>
      )}

      {/* Expanded State - Input Bar */}
      {isExpanded && (
        <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden min-w-[400px] max-w-[500px]">
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img
                src={blackCatImage}
                alt="سالی"
                className="w-8 h-8 rounded-full object-cover border-2 border-white"
              />
              <div>
                <h3 className="text-white font-semibold text-sm">دستیار سالی</h3>
                <p className="text-white/80 text-xs">دستور خود را وارد کنید</p>
              </div>
            </div>
            {!isExecuting && (
              <button
                onClick={() => {
                  setIsExpanded(false);
                  setCommand('');
                  setShowResult(false);
                }}
                className="text-white/80 hover:text-white transition-colors p-1"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Input Area */}
          <div className="p-4">
            <div className="flex items-center gap-2">
              <div className="flex-1 relative">
                <Input
                  ref={inputRef}
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="مثلاً: یک ادمین جدید با نام 'احمد احمدی' بساز..."
                  className="pr-12 border-gray-300 focus:border-purple-500 focus:ring-purple-500"
                  disabled={isExecuting}
                />
                {command.trim() && !isExecuting && (
                  <button
                    onClick={() => setCommand('')}
                    className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
              <Button
                onClick={handleExecute}
                disabled={isExecuting || !command.trim()}
                className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 px-4 h-10"
                size="sm"
              >
                {isExecuting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>

            {/* Quick Examples */}
            {!command.trim() && !isExecuting && (
              <div className="mt-3 space-y-1">
                <p className="text-xs text-gray-500 mb-2">مثال‌های سریع:</p>
                <div className="flex flex-wrap gap-2">
                  {[
                    "ساخت ادمین",
                    "لیست کاربران",
                    "ایجاد مقاله",
                  ].map((example, index) => (
                    <button
                      key={index}
                      onClick={() => setCommand(example)}
                      className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full transition-colors"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Loading State */}
            {isExecuting && (
              <div className="mt-3 flex items-center gap-2 text-sm text-gray-600">
                <Loader2 className="h-4 w-4 animate-spin text-purple-600" />
                <span>در حال اجرای دستور...</span>
              </div>
            )}
          </div>

          {/* Result Display */}
          {showResult && result && (
            <div className="border-t border-gray-200 bg-gray-50">
              <div className="p-4">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    {result.startsWith('خطا') ? (
                      <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
                    )}
                    <span className="text-xs font-medium text-gray-700">
                      {result.startsWith('خطا') ? 'خطا' : 'موفق'}
                    </span>
                  </div>
                  <button
                    onClick={handleCloseResult}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
                <p
                  className={`text-sm whitespace-pre-wrap ${
                    result.startsWith('خطا') ? 'text-red-700' : 'text-gray-800'
                  }`}
                >
                  {result.replace(/^خطا: /, '')}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SallyFloatingAgent;
