import * as React from "react"
import { cn } from "../../lib/utils"

interface CategoryBadgeProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'color'> {
  color?: string | null
  children: React.ReactNode
}

export function CategoryBadge({
  color = "#6B7280",
  children,
  className,
  ...props
}: CategoryBadgeProps) {
  // Calculate text color based on background color for better contrast
  const getContrastColor = (hexColor: string) => {
    // Remove # if present
    const cleanColor = hexColor.replace('#', '')
    
    // Convert to RGB
    const r = parseInt(cleanColor.substring(0, 2), 16)
    const g = parseInt(cleanColor.substring(2, 4), 16)
    const b = parseInt(cleanColor.substring(4, 6), 16)
    
    // Calculate luminance
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    
    // Return white text for dark colors, black text for light colors
    return luminance > 0.5 ? '#000000' : '#ffffff'
  }

  // Handle null/undefined color
  const safeColor = color || "#6B7280"
  const textColor = getContrastColor(safeColor)
  
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors",
        className
      )}
      style={{
        backgroundColor: safeColor,
        color: textColor,
        border: `1px solid ${safeColor}20` // Add subtle border with alpha
      }}
      {...props}
    >
      {children}
    </div>
  )
}

export default CategoryBadge