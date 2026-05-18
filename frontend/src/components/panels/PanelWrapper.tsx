import { motion } from "framer-motion";
import { ReactNode } from "react";

interface Props {
  title: string;
  children: ReactNode;
  corner: "tl" | "tr" | "bl" | "br";
}

export function PanelWrapper({ title, children, corner }: Props) {
  const align =
    corner === "tl"
      ? "col-start-1 row-start-1"
      : corner === "tr"
      ? "col-start-2 row-start-1"
      : corner === "bl"
      ? "col-start-1 row-start-2"
      : "col-start-2 row-start-2";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`${align} pointer-events-auto bg-black/40 backdrop-blur-sm border border-jcyan/40 rounded-lg p-3 overflow-hidden flex flex-col`}
    >
      <div className="text-xs uppercase tracking-widest text-jcyan mb-2 border-b border-jcyan/20 pb-1">
        {title}
      </div>
      <div className="flex-1 overflow-auto text-sm space-y-2 pr-1">{children}</div>
    </motion.div>
  );
}
