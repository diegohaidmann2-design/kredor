import * as React from "react"
import { format } from "date-fns"
import { ptBR } from "date-fns/locale"
import { CalendarIcon, X } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

/**
 * DatePickerBR - Componente de seleção de data no formato brasileiro (dd/MM/yyyy)
 * 
 * @param {Date|null} value - Data selecionada
 * @param {function} onChange - Callback quando a data muda (recebe Date ou null)
 * @param {string} placeholder - Texto placeholder
 * @param {string} className - Classes CSS adicionais
 * @param {boolean} clearable - Se pode limpar a data selecionada
 * @param {string} testId - data-testid para testes
 */
function DatePickerBR({
  value,
  onChange,
  placeholder = "Selecione uma data",
  className,
  clearable = true,
  testId,
  disabled = false,
}) {
  const [open, setOpen] = React.useState(false)

  const handleSelect = (date) => {
    onChange(date || null)
    setOpen(false)
  }

  const handleClear = (e) => {
    e.stopPropagation()
    onChange(null)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          disabled={disabled}
          className={cn(
            "w-full justify-start text-left font-normal bg-background border-border hover:bg-muted/50",
            !value && "text-muted-foreground",
            className
          )}
          data-testid={testId}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {value ? (
            <span className="flex-1">
              {format(value, "dd/MM/yyyy", { locale: ptBR })}
            </span>
          ) : (
            <span className="flex-1">{placeholder}</span>
          )}
          {clearable && value && (
            <X 
              className="h-4 w-4 opacity-50 hover:opacity-100 transition-opacity" 
              onClick={handleClear}
            />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0 bg-card border-border" align="start">
        <Calendar
          mode="single"
          selected={value}
          onSelect={handleSelect}
          locale={ptBR}
          initialFocus
          formatters={{
            formatCaption: (date, options) => {
              return format(date, "LLLL yyyy", { locale: ptBR })
            },
          }}
        />
      </PopoverContent>
    </Popover>
  )
}

export { DatePickerBR }
