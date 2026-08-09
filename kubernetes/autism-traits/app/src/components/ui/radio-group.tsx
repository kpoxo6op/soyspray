import * as RadioGroupPrimitive from "@radix-ui/react-radio-group";
import { Check } from "lucide-react";
import type { ComponentPropsWithoutRef } from "react";

import { cn } from "@/lib/utils";

export const RadioGroup = ({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Root>) => (
  <RadioGroupPrimitive.Root className={cn("grid gap-2", className)} {...props} />
);

type RadioOptionProps = ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Item> & {
  label: string;
};

export const RadioOption = ({ className, label, ...props }: RadioOptionProps) => (
  <RadioGroupPrimitive.Item
    className={cn(
      "group flex min-h-12 w-full items-center gap-3 rounded-2xl border border-stone-300 bg-stone-50 px-4 py-3 text-left text-stone-800 transition-colors hover:border-emerald-700 hover:bg-emerald-50 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 data-[state=checked]:border-2 data-[state=checked]:border-emerald-900 data-[state=checked]:bg-emerald-50 data-[state=checked]:font-semibold",
      className,
    )}
    {...props}
  >
    <span className="grid size-6 shrink-0 place-items-center rounded-full border-2 border-stone-500 bg-white group-data-[state=checked]:border-emerald-900 group-data-[state=checked]:bg-emerald-900">
      <RadioGroupPrimitive.Indicator>
        <Check aria-hidden="true" className="size-4 text-white" strokeWidth={3} />
      </RadioGroupPrimitive.Indicator>
    </span>
    <span>{label}</span>
  </RadioGroupPrimitive.Item>
);
