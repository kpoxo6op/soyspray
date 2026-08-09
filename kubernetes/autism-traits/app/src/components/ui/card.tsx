import type { HTMLAttributes } from "react";

export const Card = ({ className, ...props }: HTMLAttributes<HTMLElement>) => (
  <section className={className} {...props} />
);
