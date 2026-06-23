import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        "h-10 w-full min-w-0 rounded-lg border border-input bg-white/5 px-3 py-1 text-sm text-foreground backdrop-blur-sm transition-colors outline-none placeholder:text-muted-foreground",
        // Style the native file picker as an inline Azure-blue pill — purely visual, no JS.
        "file:mr-3 file:inline-flex file:h-7 file:cursor-pointer file:rounded-md file:border-0 file:bg-primary/10 file:px-3 file:text-sm file:font-medium file:text-primary file:transition-colors hover:file:bg-primary/15",
        "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-muted/60 disabled:opacity-60 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:bg-input/30 dark:disabled:bg-input/80 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40",
        className
      )}
      {...props}
    />
  )
}

export { Input }
