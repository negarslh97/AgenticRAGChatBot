"use client"

import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { toast } from "react-hot-toast"

interface Ticket {
  id: string
  title: string
  status: "open" | "in_progress" | "resolved" | "closed"
  priority: "low" | "medium" | "high" | "urgent"
  created_at: string
  updated_at: string
}

const TicketsPage: React.FC = () => {
  const { user } = useAuth()
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState("all")

  useEffect(() => {
    fetchTickets()
  }, [])

  const fetchTickets = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/tickets/`, {
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        }
      })

      if (!response.ok) {
        throw new Error("خطا در دریافت تیکت‌ها")
      }

      const data = await response.json()
      setTickets(data.tickets)
    } catch (error: any) {
      toast.error(error.message || "خطا در دریافت تیکت‌ها")
    } finally {
      setLoading(false)
    }
  }

  const getFilteredTickets = () => {
    if (activeTab === "all") return tickets
    return tickets.filter(ticket => ticket.status === activeTab)
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "urgent":
        return "bg-red-600 text-white"
      case "high":
        return "bg-orange-600 text-white"
      case "medium":
        return "bg-yellow-600 text-white"
      case "low":
        return "bg-green-600 text-white"
      default:
        return "bg-gray-600 text-white"
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <Link
                to="/"
                className="text-gray-600 hover:text-gray-900 transition-colors"
              >
                ← بازگشت به خانه
              </Link>
              <h1 className="text-2xl font-bold text-gray-900">
                تیکت‌های پشتیبانی
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              {user && (
                <div className="text-sm text-gray-600">
                  خوش آمدید، {user.full_name}
                </div>
              )}
              {user && (
                <div className="flex space-x-2">
                  <Link
                    to="/chat"
                    className="text-sm bg-gray-100 text-gray-700 px-3 py-1 rounded-md hover:bg-gray-200 transition-colors"
                  >
                    چت با Sally
                  </Link>
                  <Link
                    to="/knowledge-base"
                    className="text-sm bg-gray-100 text-gray-700 px-3 py-1 rounded-md hover:bg-gray-200 transition-colors"
                  >
                    پایگاه دانش
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Actions */}
        <div className="flex justify-between items-center mb-6">
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab("all")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === "all"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              همه تیکت‌ها
            </button>
            <button
              onClick={() => setActiveTab("open")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === "open"
                  ? "bg-red-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              باز ({tickets.filter(t => t.status === "open").length})
            </button>
            <button
              onClick={() => setActiveTab("in_progress")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === "in_progress"
                  ? "bg-yellow-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              در حال پردازش ({tickets.filter(t => t.status === "in_progress").length})
            </button>
            <button
              onClick={() => setActiveTab("resolved")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === "resolved"
                  ? "bg-green-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              حل شده ({tickets.filter(t => t.status === "resolved").length})
            </button>
          </div>
          
          {user && (
            <Link
              to="/tickets/create"
              className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              ایجاد تیکت جدید
            </Link>
          )}
        </div>

        {/* Tickets List */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="px-6 py-4 border-b">
            <h2 className="text-lg font-semibold text-gray-900">
              لیست تیکت‌ها ({getFilteredTickets().length})
            </h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : getFilteredTickets().length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">تیکتی یافت نشد</p>
              {activeTab !== "all" && (
                <Link
                  to="/tickets"
                  className="inline-block mt-4 text-blue-600 hover:text-blue-500"
                >
                  نمایش همه تیکت‌ها
                </Link>
              )}
            </div>
          ) : (
            <div className="divide-y">
              {getFilteredTickets().map((ticket) => (
                <div key={ticket.id} className="p-6 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <h3 className="text-lg font-medium text-gray-900">
                          {ticket.title}
                        </h3>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${(() => {
                          const colors = {
                            open: "bg-blue-100 text-blue-800",
                            in_progress: "bg-yellow-100 text-yellow-800",
                            resolved: "bg-green-100 text-green-800",
                            closed: "bg-gray-100 text-gray-800",
                          };
                          return colors[ticket.status as keyof typeof colors] || "bg-gray-100 text-gray-800";
                        })()}`}>
                          {ticket.status === "open" && "باز"}
                          {ticket.status === "in_progress" && "در حال پردازش"}
                          {ticket.status === "resolved" && "حل شده"}
                          {ticket.status === "closed" && "بسته شده"}
                        </span>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(ticket.priority)}`}>
                          {ticket.priority === "urgent" && "فوری"}
                          {ticket.priority === "high" && "بالا"}
                          {ticket.priority === "medium" && "متوسط"}
                          {ticket.priority === "low" && "پایین"}
                        </span>
                      </div>
                      
                      <div className="flex items-center space-x-4 mt-3 text-sm text-gray-500">
                        <span>
                          ایجاد شده: {new Date(ticket.created_at).toLocaleDateString("fa-IR")}
                        </span>
                        <span>
                          به‌روزرسانی: {new Date(ticket.updated_at).toLocaleDateString("fa-IR")}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 ml-4">
                      <Link
                        to={`/tickets/${ticket.id}`}
                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                      >
                        مشاهده
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TicketsPage
