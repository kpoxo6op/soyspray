import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export const Card = ({ className, ...props }: HTMLAttributes<HTMLElement>) => (
  <section
    className={cn("rounded-3xl border border-stone-300 bg-white/85 shadow-sm", className)}
    {...props}
  />
);
