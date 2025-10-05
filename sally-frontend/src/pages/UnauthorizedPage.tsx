import React from "react"
import { Link } from "react-router-dom"
import { Button } from "../components/ui/button"
import { ShieldAlert } from "lucide-react"

const UnauthorizedPage: React.FC = () => {
  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-50">
      <main className="flex items-center justify-center flex-1">
        <div className="text-center">
          <div className="flex justify-center mb-6">
            <div className="p-6 bg-red-100 rounded-full">
              <ShieldAlert className="h-20 w-20 text-red-600" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-4">دسترسی غیرمجاز</h1>
          <p className="text-gray-600 mb-6">شما دسترسی لازم برای مشاهده این صفحه را ندارید.</p>
          <div className="space-x-4">
            <Link to="/">
              <Button>بازگشت به صفحه اصلی</Button>
            </Link>
            <Link to="/login">
              <Button variant="outline">ورود به سیستم</Button>
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}

export default UnauthorizedPage