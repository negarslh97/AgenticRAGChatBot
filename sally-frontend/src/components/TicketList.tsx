"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { ticketService, type Ticket } from "../services/ticketService"
import { useAuth } from "../context/AuthContext"
import toast from "react-hot-toast"

interface TicketListProps {
  isadminView?: boolean
}

const TicketList: React.FC<TicketListProps> = ({ isadminView = false }) => {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>("all")
  const { user } = useAuth()

  useEffect(() => {
    loadTickets()
  }, [isadminView])

  const loadTickets = async () => {
    try {
      const ticketData = isadminView ? await ticketService.getAllTickets() : await ticketService.getUserTickets()
      setTickets(ticketData)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to load tickets")
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    const colors = {
      open: "bg-blue-100 text-blue-800",
      in_progress: "bg-yellow-100 text-yellow-800",
      resolved: "bg-green-100 text-green-800",
      closed: "bg-gray-100 text-gray-800",
    }
    return colors[status as keyof typeof colors] || "bg-gray-100 text-gray-800"
  }

  const getPriorityColor = (priority: string) => {
    const colors = {
      low: "bg-gray-100 text-gray-800",
      medium: "bg-blue-100 text-blue-800",
      high: "bg-orange-100 text-orange-800",
      urgent: "bg-red-100 text-red-800",
    }
    return colors[priority as keyof typeof colors] || "bg-gray-100 text-gray-800"
  }

  const filteredTickets = tickets.filter((ticket) => {
    if (filter === "all") return true
    return ticket.status === filter
  })

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="card">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-1/4"></div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div>
      {/* Filter Tabs */}
      <div className="mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {["all", "open", "in_progress", "resolved", "closed"].map((status) => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  filter === status
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                {status === "all" ? "All Tickets" : status.replace("_", " ").toUpperCase()}
                <span className="ml-2 bg-gray-100 text-gray-900 py-0.5 px-2.5 rounded-full text-xs">
                  {status === "all" ? tickets.length : tickets.filter((t) => t.status === status).length}
                </span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Tickets */}
      {filteredTickets.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 text-6xl mb-4">🎫</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No tickets found</h3>
          <p className="text-gray-500 mb-4">
            {filter === "all" ? "You haven't created any tickets yet." : `No ${filter} tickets found.`}
          </p>
          {!isadminView && (
            <Link to="/tickets/new" className="btn-primary">
              Create Your First Ticket
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredTickets.map((ticket) => (
            <div key={ticket.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <h3 className="text-lg font-medium text-gray-900">
                      <Link
                        to={isadminView ? `/admin/tickets/${ticket.id}` : `/tickets/${ticket.id}`}
                        className="hover:text-blue-600 transition-colors"
                      >
                        {ticket.title}
                      </Link>
                    </h3>
                  </div>

                  <p className="text-gray-600 mb-3 line-clamp-2">{ticket.description}</p>

                  <div className="flex items-center space-x-4 text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${(() => {
                      const colors = {
                        open: "bg-blue-100 text-blue-800",
                        in_progress: "bg-yellow-100 text-yellow-800",
                        resolved: "bg-green-100 text-green-800",
                        closed: "bg-gray-100 text-gray-800",
                      };
                      return colors[ticket.status as keyof typeof colors] || "bg-gray-100 text-gray-800";
                    })()}`}>
                      {ticket.status.replace("_", " ").toUpperCase()}
                    </span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(ticket.priority)}`}>
                      {ticket.priority.toUpperCase()}
                    </span>
                    <span className="text-gray-500">#{ticket.id.slice(-8)}</span>
                  </div>
                </div>

                <div className="text-right text-sm text-gray-500">
                  <p>Created {new Date(ticket.created_at).toLocaleDateString()}</p>
                  <p>Updated {new Date(ticket.updated_at).toLocaleDateString()}</p>
                  {isadminView && ticket.assigned_to && <p className="text-blue-600">Assigned</p>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default TicketList
