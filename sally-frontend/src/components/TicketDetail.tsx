"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { ticketService, type Ticket, type TicketReply, type CreateReplyData } from "../services/ticketService"
import { useAuth } from "../context/AuthContext"
import toast from "react-hot-toast"

interface TicketDetailProps {
  isadminView?: boolean
}

const TicketDetail: React.FC<TicketDetailProps> = ({ isadminView = false }) => {
  const { ticketId } = useParams<{ ticketId: string }>()
  const [ticket, setTicket] = useState<Ticket | null>(null)
  const [replies, setReplies] = useState<TicketReply[]>([])
  const [newReply, setNewReply] = useState("")
  const [isInternal, setIsInternal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const { user, isAdmin } = useAuth()

  useEffect(() => {
    if (ticketId) {
      loadTicketData()
    }
  }, [ticketId])

  const loadTicketData = async () => {
    try {
      const [ticketData, repliesData] = await Promise.all([
        ticketService.getTicket(ticketId!),
        ticketService.getTicketReplies(ticketId!),
      ])
      setTicket(ticketData)
      setReplies(repliesData)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to load ticket")
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitReply = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newReply.trim()) return

    setSubmitting(true)
    try {
      const replyData: CreateReplyData = {
        content: newReply,
        is_internal: isAdmin && isInternal,
      }

      const reply = await ticketService.addReply(ticketId!, replyData)
      setReplies([...replies, reply])
      setNewReply("")
      setIsInternal(false)
      toast.success("Reply added successfully!")
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to add reply")
    } finally {
      setSubmitting(false)
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

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="card">
            <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-2/3"></div>
          </div>
        </div>
      </div>
    )
  }

  if (!ticket) {
    return (
      <div className="max-w-4xl mx-auto text-center py-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Ticket Not Found</h2>
        <Link to="/tickets" className="btn-primary">
          Back to Tickets
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Ticket Header */}
      <div className="card">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">{ticket.title}</h1>
            <div className="flex items-center space-x-4">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${(() => {
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
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getPriorityColor(ticket.priority)}`}>
                {ticket.priority.toUpperCase()} PRIORITY
              </span>
              <span className="text-gray-500 text-sm">Ticket #{ticket.id.slice(-8)}</span>
            </div>
          </div>
          <div className="text-right text-sm text-gray-500">
            <p>Created: {new Date(ticket.created_at).toLocaleString()}</p>
            <p>Updated: {new Date(ticket.updated_at).toLocaleString()}</p>
          </div>
        </div>

        <div className="border-t pt-4">
          <h3 className="font-medium text-gray-900 mb-2">Description</h3>
          <p className="text-gray-700 whitespace-pre-wrap">{ticket.description}</p>
        </div>
      </div>

      {/* Replies */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Conversation ({replies.length} {replies.length === 1 ? "reply" : "replies"})
        </h3>

        <div className="space-y-4">
          {replies.map((reply) => (
            <div
              key={reply.id}
              className={`p-4 rounded-lg ${reply.is_internal ? "bg-yellow-50 border border-yellow-200" : "bg-gray-50"}`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="font-medium text-gray-900">
                    {reply.user_id === user?.id ? "You" : "Support Team"}
                  </span>
                  {reply.is_internal && (
                    <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">Internal Note</span>
                  )}
                </div>
                <span className="text-sm text-gray-500">{new Date(reply.created_at).toLocaleString()}</span>
              </div>
              <p className="text-gray-700 whitespace-pre-wrap">{reply.content}</p>
            </div>
          ))}
        </div>

        {/* Reply Form */}
        <div className="mt-6 pt-6 border-t">
          <form onSubmit={handleSubmitReply} className="space-y-4">
            <div>
              <label htmlFor="reply" className="block text-sm font-medium text-gray-700 mb-2">
                Add Reply
              </label>
              <textarea
                id="reply"
                rows={4}
                className="input-field"
                placeholder="Type your reply here..."
                value={newReply}
                onChange={(e) => setNewReply(e.target.value)}
                required
              />
            </div>

            {isAdmin && (
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="internal"
                  checked={isInternal}
                  onChange={(e) => setIsInternal(e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label htmlFor="internal" className="ml-2 block text-sm text-gray-700">
                  Internal note (not visible to customer)
                </label>
              </div>
            )}

            <div className="flex items-center justify-between">
              <Link
                to={isadminView ? "/admin/tickets" : "/tickets"}
                className="text-gray-600 hover:text-gray-800 transition-colors"
              >
                ← Back to Tickets
              </Link>
              <button type="submit" className="btn-primary" disabled={submitting}>
                {submitting ? "Sending..." : "Send Reply"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default TicketDetail
