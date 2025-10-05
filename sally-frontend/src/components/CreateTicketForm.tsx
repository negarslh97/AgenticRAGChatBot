"use client"

import type React from "react"
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { ticketService, type CreateTicketData } from "../services/ticketService"
import { Button } from "./ui/button"
import toast from "react-hot-toast"

const CreateTicketForm: React.FC = () => {
  const [formData, setFormData] = useState<CreateTicketData>({
    title: "",
    description: "",
    priority: "medium",
  })
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      const ticket = await ticketService.createTicket(formData)
      toast.success("Ticket created successfully!")
      navigate(`/tickets/${ticket.id}`)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to create ticket")
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Create Support Ticket</h2>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
              Title *
            </label>
            <input
              type="text"
              id="title"
              name="title"
              required
              className="input-field"
              placeholder="Brief description of your issue"
              value={formData.title}
              onChange={handleChange}
            />
          </div>

          <div>
            <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-2">
              Priority
            </label>
            <select
              id="priority"
              name="priority"
              className="input-field"
              value={formData.priority}
              onChange={handleChange}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
              Description *
            </label>
            <textarea
              id="description"
              name="description"
              required
              rows={6}
              className="input-field"
              placeholder="Please provide detailed information about your issue, including steps to reproduce if applicable"
              value={formData.description}
              onChange={handleChange}
            />
          </div>

          <div className="flex items-center justify-between">
            <Button type="button" onClick={() => navigate("/tickets")} variant="secondary" disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Creating..." : "Create Ticket"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default CreateTicketForm
