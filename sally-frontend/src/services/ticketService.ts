import api from "./authService"

export interface Ticket {
  id: string
  title: string
  description: string
  status: "open" | "in_progress" | "resolved" | "closed"
  priority: "low" | "medium" | "high" | "urgent"
  created_at: string
  updated_at: string
  assigned_to?: string
}

export interface TicketReply {
  id: string
  content: string
  user_id: string
  is_internal: boolean
  created_at: string
}

export interface CreateTicketData {
  title: string
  description: string
  priority: string
}

export interface CreateReplyData {
  content: string
  is_internal?: boolean
}

export const ticketService = {
  async createTicket(ticketData: CreateTicketData): Promise<Ticket> {
    const response = await api.post("/tickets/", ticketData)
    return response.data
  },

  async getUserTickets(): Promise<Ticket[]> {
    const response = await api.get("/tickets/")
    return response.data
  },

  async getTicket(ticketId: string): Promise<Ticket> {
    const response = await api.get(`/tickets/${ticketId}`)
    return response.data
  },

  async addReply(ticketId: string, replyData: CreateReplyData): Promise<TicketReply> {
    const response = await api.post(`/tickets/${ticketId}/replies`, replyData)
    return response.data
  },

  async getTicketReplies(ticketId: string): Promise<TicketReply[]> {
    const response = await api.get(`/tickets/${ticketId}/replies`)
    return response.data
  },

  // admin functions
  async getAllTickets(): Promise<Ticket[]> {
    const response = await api.get("/admin/tickets")
    return response.data
  },

  async assignTicket(ticketId: string, assignedTo?: string): Promise<void> {
    await api.put(`/admin/tickets/${ticketId}/assign`, { assigned_to: assignedTo })
  },

  async updateTicketStatus(ticketId: string, status: string): Promise<void> {
    await api.put(`/admin/tickets/${ticketId}/status`, { status })
  },
}
