import React, { useEffect, useState } from 'react';
import { X, Sparkles } from 'lucide-react';
import { Button } from './ui/button';
import api from '../services/authService';

interface ArticleHighlightModalProps {
  articleId: string;
  userQuery: string;
  onClose: () => void;
}

interface Article {
  id: string;
  title: string;
  content: string;
  summary: string;
  category?: string;
  tags: string[];
  highlight_keywords: string[];
  created_at: string;
  updated_at: string;
}

const ArticleHighlightModal: React.FC<ArticleHighlightModalProps> = ({
  articleId,
  userQuery,
  onClose,
}) => {
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchArticle = async () => {
      try {
        console.log('🔍 Fetching article:', articleId);
        console.log('📝 User query:', userQuery);
        
        const response = await api.get(`/api/article/${articleId}`, {
          params: { query: userQuery }
        });
        
        console.log('✅ Article fetched:', response.data);
        console.log('🎯 Highlight keywords:', response.data.highlight_keywords);
        
        setArticle(response.data);
      } catch (error) {
        console.error('❌ Failed to fetch article:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchArticle();
  }, [articleId, userQuery]);

  // 🔥 تابع هوشمند برای highlight کردن متن
  const highlightText = (text: string, keywords: string[]): React.ReactNode => {
    if (!keywords || keywords.length === 0) {
      console.log('⚠️ No keywords for highlighting');
      return text;
    }

    console.log('🎨 Highlighting text with keywords:', keywords);

    // Escape special regex characters in keywords
    const escapedKeywords = keywords.map(kw => 
      kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    );

    // ساخت regex برای پیدا کردن کلمات کلیدی (case-insensitive & word boundaries)
    const pattern = new RegExp(`(${escapedKeywords.join('|')})`, 'gi');
    const parts = text.split(pattern);

    console.log('📊 Split into parts:', parts.length);

    return parts.map((part, index) => {
      const isKeyword = keywords.some(
        keyword => part.toLowerCase().trim() === keyword.toLowerCase().trim()
      );

      if (isKeyword) {
        console.log('✨ Highlighting:', part);
        return (
          <mark
            key={index}
            className="bg-yellow-300 text-gray-900 px-1 rounded font-bold"
            style={{ 
              backgroundColor: '#fef08a',
              padding: '2px 4px',
              borderRadius: '3px'
            }}
          >
            {part}
          </mark>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  // 🔥 پردازش محتوای Markdown برای نمایش با highlight
  const renderHighlightedContent = () => {
    if (!article) {
      console.log('⚠️ No article to render');
      return null;
    }

    console.log('📝 Rendering content with length:', article.content.length);
    console.log('🎯 Keywords to highlight:', article.highlight_keywords);

    // تقسیم content به خطوط
    const lines = article.content.split('\n');
    console.log('📊 Total lines:', lines.length);
    
    return lines.map((line, index) => {
      // چک کردن اینکه خط شامل هدر Markdown هست یا نه
      if (line.startsWith('#')) {
        const level = line.match(/^#+/)?.[0].length || 1;
        const text = line.replace(/^#+\s*/, '');
        const Tag = `h${Math.min(level, 6)}` as keyof JSX.IntrinsicElements;
        
        return (
          <Tag key={index} className={`font-bold mb-3 mt-4 text-right ${
            level === 1 ? 'text-3xl text-blue-800' : 
            level === 2 ? 'text-2xl text-blue-700' : 
            'text-xl text-blue-600'
          }`}>
            {highlightText(text, article.highlight_keywords)}
          </Tag>
        );
      }
      
      // چک کردن اینکه خط لیست هست
      if (line.match(/^[-*]\s/)) {
        const text = line.replace(/^[-*]\s/, '');
        return (
          <li key={index} className="mr-6 mb-1 text-right list-disc">
            {highlightText(text, article.highlight_keywords)}
          </li>
        );
      }
      
      // خط عادی
      if (line.trim()) {
        return (
          <p key={index} className="mb-3 text-right leading-8 text-gray-700">
            {highlightText(line, article.highlight_keywords)}
          </p>
        );
      }
      
      return <br key={index} />;
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b bg-gradient-to-r from-blue-600 to-purple-600 text-white">
          <div className="flex items-center gap-3 flex-1">
            <Sparkles className="h-6 w-6 animate-pulse" />
            <div className="flex-1">
              <h2 className="text-xl font-bold text-right">
                {loading ? 'در حال بارگذاری...' : article?.title}
              </h2>
              {article?.summary && (
                <p className="text-sm opacity-90 text-right mt-1">{article.summary}</p>
              )}
            </div>
          </div>
          <Button
            onClick={onClose}
            variant="ghost"
            size="icon"
            className="text-white hover:bg-white/20"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Tags & Category */}
        {article && (article.tags.length > 0 || article.category) && (
          <div className="px-6 py-3 bg-gray-50 border-b flex gap-2 items-center justify-end flex-wrap">
            {article.category && (
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                📁 {article.category}
              </span>
            )}
            {article.tags.map((tag, index) => (
              <span key={index} className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm">
                🏷️ {tag}
              </span>
            ))}
          </div>
        )}

        {/* Highlight Info */}
        {article && (
          article.highlight_keywords.length > 0 ? (
            <div className="px-6 py-3 bg-yellow-50 border-b flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-yellow-600" />
              <p className="text-sm text-yellow-800 text-right flex-1">
                ✨ کلمات مرتبط با سوال شما به رنگ <span className="bg-yellow-300 px-1 rounded font-bold">زرد</span> highlighted شده‌اند:
                <span className="font-semibold mr-2">
                  {article.highlight_keywords.join('، ')}
                </span>
              </p>
            </div>
          ) : (
            <div className="px-6 py-3 bg-blue-50 border-b flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-blue-600" />
              <p className="text-sm text-blue-800 text-right flex-1">
                💡 این مقاله مرتبط با سوال شماست
              </p>
            </div>
          )
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <>
              {/* 🔥 Debug Info - نمایش کلمات کلیدی */}
              {article && article.highlight_keywords.length > 0 && (
                <div className="mb-4 p-3 bg-gray-100 rounded text-sm">
                  <strong>🔍 Debug - کلمات جستجو:</strong>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {article.highlight_keywords.map((kw, i) => (
                      <span key={i} className="bg-yellow-200 px-2 py-1 rounded">
                        "{kw}"
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="prose prose-lg max-w-none text-gray-800">
                {renderHighlightedContent()}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
          <Button onClick={onClose} className="bg-blue-600 hover:bg-blue-700">
            بستن
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ArticleHighlightModal;

