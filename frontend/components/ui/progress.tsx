import * as React from "react";

import { cn } from "@/lib/utils";

// Minimal, dependency-free progress bar (shadcn's ships a Radix/Base-UI primitive we don't need
// for a simple upload indicator). Driven by a 0–100 `value`.
function Progress({
  value = 0,
  className,
  ...props
}: React.ComponentProps<"div"> & { value?: number }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      className={cn("relative h-2 w-full overflow-hidden rounded-full bg-primary/20", className)}
      {...props}
    >
      <div
        className="h-full bg-primary transition-all duration-150 ease-out"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export { Progress };
