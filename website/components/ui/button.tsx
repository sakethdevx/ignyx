"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-full text-sm font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-electric-400/70 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-gradient-to-r from-electric-500 via-electric-400 to-violet-500 px-6 py-3 text-white shadow-glow hover:scale-[1.02] hover:shadow-[0_20px_90px_rgba(67,135,255,0.3)]",
        secondary:
          "border border-white/12 bg-white/6 px-6 py-3 text-foreground backdrop-blur-xl hover:border-electric-400/40 hover:bg-white/10",
        ghost:
          "px-4 py-2 text-muted hover:bg-white/6 hover:text-foreground",
      },
      size: {
        default: "h-11",
        lg: "h-12 px-7 text-base",
        sm: "h-9 px-4 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
