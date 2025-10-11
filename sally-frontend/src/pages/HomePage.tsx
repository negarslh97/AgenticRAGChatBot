"use client"

import { Link } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { Button } from "../components/ui/button"
import { Bot, BookOpen, Target, Ticket, Shield, Zap } from "lucide-react"

const HomePage: React.FC = () => {
  const { user, isAuthenticated } = useAuth()

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 to-secondary/10">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center fade-in">
            <h1 className="text-4xl md:text-6xl font-bold text-foreground mb-6">
              به پلتفرم پشتیبانی هوشمند Sally خوش آمدید
            </h1>
            <p className="text-xl text-muted-foreground mb-8 max-w-3xl mx-auto">
              دستیار هوشمند Sally آماده است تا به شما در حل مشکلات و پاسخگویی به سوالات کمک کند
            </p>
            <div className="flex flex-col items-center gap-6">
              {!isAuthenticated ? (
                <>
                  {/* New prominent primary button for guest users */}
                  <Link to="/chat">
                    <Button size="lg" className="px-8 py-6 text-lg">
                      چت با Sally
                    </Button>
                  </Link>
                  
                  {/* Secondary buttons for login/signup */}
                  <div className="flex flex-col sm:flex-row gap-4">
                    <Link to="/login">
                      <Button variant="outline" size="lg">
                        ورود به حساب
                      </Button>
                    </Link>
                    <Link to="/register">
                      <Button variant="outline" size="lg">
                        ثبت‌نام جدید
                      </Button>
                    </Link>
                  </div>
                </>
              ) : (
                <Link to="/chat">
                  <Button size="lg" className="px-8 py-3 text-lg">
                    شروع چت با Sally
                  </Button>
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h2 className="text-3xl font-bold text-center text-foreground mb-12">
          ویژگی‌های پلتفرم Sally
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          <div className="card p-6 text-center hover:scale-105 transition-transform duration-300">
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-blue-100 rounded-full">
                <Bot className="h-10 w-10 text-blue-600" />
              </div>
            </div>
            <h3 className="text-xl font-semibold text-foreground mb-2">هوش مصنوعی پیشرفته</h3>
            <p className="text-muted-foreground">
              Sally با استفاده از هوش مصنوعی پیشرفته به سوالات شما به صورت هوشمند پاسخ می‌دهد
            </p>
          </div>
          
          <div className="card p-6 text-center hover:scale-105 transition-transform duration-300">
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-purple-100 rounded-full">
                <BookOpen className="h-10 w-10 text-purple-600" />
              </div>
            </div>
            <h3 className="text-xl font-semibold text-foreground mb-2">پایگاه دانش گسترده</h3>
            <p className="text-muted-foreground">
              دسترسی به هزاران مقاله و راهنما برای حل مشکلات مختلف
            </p>
          </div>
          
          <div className="card p-6 text-center hover:scale-105 transition-transform duration-300">
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-green-100 rounded-full">
                <Target className="h-10 w-10 text-green-600" />
              </div>
            </div>
            <h3 className="text-xl font-semibold text-foreground mb-2">پشتیبانی ۲۴ ساعته</h3>
            <p className="text-muted-foreground">
              Sally در طول شبانه‌روز آماده پاسخگویی به نیازهای شماست
            </p>
          </div>
          
          <div className="card p-6 text-center hover:scale-105 transition-transform duration-300">
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-orange-100 rounded-full">
                <Ticket className="h-10 w-10 text-orange-600" />
              </div>
            </div>
            <h3 className="text-xl font-semibold text-foreground mb-2">سیستم تیکتینگ</h3>
            <p className="text-muted-foreground">
              ایجاد و پیگیری تیکت‌های پشتیبانی برای مشکلات پیچیده
            </p>
          </div>
          
          <div className="card p-6 text-center hover:scale-105 transition-transform duration-300">
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-red-100 rounded-full">
                <Shield className="h-10 w-10 text-red-600" />
              </div>
            </div>
            <h3 className="text-xl font-semibold text-foreground mb-2">امنیت بالا</h3>
            <p className="text-muted-foreground">
              تمام داده‌های شما با بالاترین استانداردهای امنیتی محافظت می‌شوند
            </p>
          </div>
          
          <div className="card p-6 text-center hover:scale-105 transition-transform duration-300">
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-yellow-100 rounded-full">
                <Zap className="h-10 w-10 text-yellow-600" />
              </div>
            </div>
            <h3 className="text-xl font-semibold text-foreground mb-2">پاسخ فوری</h3>
            <p className="text-muted-foreground">
              دریافت پاسخ‌های فوری و دقیق در کمترین زمان ممکن
            </p>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-primary text-primary-foreground py-16">
        <div className="max-w-4xl mx-auto text-center px-4 fade-in">
          <h2 className="text-3xl font-bold mb-4">
            آماده هستید تا از Sally استفاده کنید؟
          </h2>
          <p className="text-xl mb-8 opacity-90">
            همین امروز حساب کاربری خود را ایجاد کرده و از تمام ویژگی‌های پلتفرم استفاده کنید
          </p>
          {!user && (
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/register">
                <Button 
                  size="lg"
                  className="bg-white text-blue-600 hover:bg-gray-100 px-8 py-3 text-lg rounded-full"
                >
                  ثبت‌نام رایگان
                </Button>
              </Link>
              <Link to="/login">
                <Button 
                  size="lg"
                  variant="outline"
                  className="border-2 border-white text-white hover:bg-white hover:text-blue-600 px-8 py-3 text-lg rounded-full"
                >
                  ورود به حساب
                </Button>
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-muted text-foreground py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-muted-foreground">
            © ۱۴۰۳ Sally. تمام حقوق محفوظ است.
          </p>
        </div>
      </footer>
    </div>
  )
}

export default HomePage
