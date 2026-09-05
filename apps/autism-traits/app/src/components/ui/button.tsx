import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "inline-flex min-h-12 items-center justify-center gap-2 rounded-full px-6 text-base font-semibold transition-colors focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-emerald-800 disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        primary: "bg-emerald-950 text-stone-50 hover:bg-emerald-900",
        secondary:
          "border border-stone-400 bg-stone-50 text-emerald-950 hover:border-emerald-800 hover:bg-emerald-50",
        quiet: "text-emerald-950 underline-offset-4 hover:bg-stone-200 hover:underline",
        danger: "border border-red-700 bg-stone-50 text-red-800 hover:bg-red-50",
      },
    },
    defaultVariants: { variant: "primary" },
  },
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;

export const Button = ({ className, variant, type = "button", ...props }: ButtonProps) => (
  <button type={type} className={cn(buttonVariants({ variant }), className)} {...props} />
);
