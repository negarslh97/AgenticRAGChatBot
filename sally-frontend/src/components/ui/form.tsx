import * as React from "react"
import { Label } from "./label"
import { Input } from "./input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./select"
import { Button } from "./button"

export interface FormFieldProps {
  label: string
  name: string
  type?: string
  placeholder?: string
  value: string
  onChange: (value: string) => void
  required?: boolean
  disabled?: boolean
  error?: string
  className?: string
  children?: React.ReactNode
}

export interface FormSelectFieldProps {
  label: string
  name: string
  value: string
  onChange: (value: string) => void
  options: Array<{
    value: string
    label: string
    disabled?: boolean
  }>
  placeholder?: string
  required?: boolean
  disabled?: boolean
  loading?: boolean
  loadingText?: string
  emptyText?: string
  className?: string
  children?: React.ReactNode
}

export interface FormProps {
  children: React.ReactNode
  onSubmit: (e: React.FormEvent) => void
  className?: string
}

// Text Input Field
export const FormField: React.FC<FormFieldProps> = ({
  label,
  name,
  type = "text",
  placeholder,
  value,
  onChange,
  required = false,
  disabled = false,
  error,
  className = "",
  children
}) => {
  return (
    <div className={`space-y-2 ${className}`}>
      <Label htmlFor={name} className={error ? "text-red-600" : ""}>
        {label}
        {required && <span className="text-red-500 mr-1">*</span>}
      </Label>
      <div className="relative">
        {children}
        <Input
          id={name}
          name={name}
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          required={required}
          className={error ? "border-red-500 focus:ring-red-500" : ""}
        />
      </div>
      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}
    </div>
  )
}

// Select Field
export const FormSelectField: React.FC<FormSelectFieldProps> = ({
  label,
  name,
  value,
  onChange,
  options,
  placeholder = "انتخاب کنید...",
  required = false,
  disabled = false,
  loading = false,
  loadingText = "در حال بارگذاری...",
  emptyText = "گزینه‌ای یافت نشد",
  className = "",
  children
}) => {
  return (
    <div className={`space-y-2 ${className}`}>
      <Label htmlFor={name}>
        {label}
        {required && <span className="text-red-500 mr-1">*</span>}
      </Label>
      <Select
        value={value}
        onValueChange={onChange}
        disabled={disabled || loading}
      >
        <SelectTrigger id={name} className="relative">
          {children}
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {loading ? (
            <SelectItem value="loading" disabled>
              {loadingText}
            </SelectItem>
          ) : options.length > 0 ? (
            options.map((option) => (
              <SelectItem
                key={option.value}
                value={option.value}
                disabled={option.disabled}
              >
                {option.label}
              </SelectItem>
            ))
          ) : (
            <SelectItem value="empty" disabled>
              {emptyText}
            </SelectItem>
          )}
        </SelectContent>
      </Select>
    </div>
  )
}

// Form Container
export const Form: React.FC<FormProps> = ({
  children,
  onSubmit,
  className = ""
}) => {
  return (
    <form onSubmit={onSubmit} className={`space-y-6 ${className}`}>
      {children}
    </form>
  )
}

// Form Actions Container
export interface FormActionsProps {
  children: React.ReactNode
  className?: string
}

export const FormActions: React.FC<FormActionsProps> = ({
  children,
  className = ""
}) => {
  return (
    <div className={`flex gap-3 justify-end ${className}`}>
      {children}
    </div>
  )
}

// Submit Button
export interface SubmitButtonProps {
  children: React.ReactNode
  loading?: boolean
  loadingText?: string
  disabled?: boolean
  className?: string
}

export const SubmitButton: React.FC<SubmitButtonProps> = ({
  children,
  loading = false,
  loadingText = "در حال ارسال...",
  disabled = false,
  className = ""
}) => {
  return (
    <Button
      type="submit"
      disabled={disabled || loading}
      className={`flex items-center gap-2 ${className}`}
    >
      {loading ? (
        <>
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
          {loadingText}
        </>
      ) : (
        children
      )}
    </Button>
  )
}

// Cancel Button
export interface CancelButtonProps {
  children: React.ReactNode
  onClick: () => void
  disabled?: boolean
  className?: string
}

export const CancelButton: React.FC<CancelButtonProps> = ({
  children,
  onClick,
  disabled = false,
  className = ""
}) => {
  return (
    <Button
      type="button"
      variant="outline"
      onClick={onClick}
      disabled={disabled}
      className={className}
    >
      {children}
    </Button>
  )
}