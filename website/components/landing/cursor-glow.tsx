"use client";

import { motion, useMotionValue, useSpring } from "framer-motion";
import { useEffect } from "react";

export function CursorGlow() {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const smoothX = useSpring(x, { stiffness: 120, damping: 24, mass: 0.8 });
  const smoothY = useSpring(y, { stiffness: 120, damping: 24, mass: 0.8 });

  useEffect(() => {
    const handleMove = (event: MouseEvent) => {
      x.set(event.clientX);
      y.set(event.clientY);
    };

    window.addEventListener("mousemove", handleMove);
    return () => window.removeEventListener("mousemove", handleMove);
  }, [x, y]);

  return (
    <>
      <motion.div
        className="pointer-events-none fixed left-0 top-0 z-0 hidden h-[360px] w-[360px] rounded-full bg-electric-400/20 blur-[120px] lg:block"
        style={{
          x: smoothX,
          y: smoothY,
          translateX: "-50%",
          translateY: "-50%",
        }}
      />
    </>
  );
}
