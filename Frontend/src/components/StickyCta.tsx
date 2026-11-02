import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { FaWhatsapp } from "react-icons/fa6";
import { useEffect, useState } from "react";

import { BRAND } from "../lib/brand";
import { useWhatsapp } from "../hooks/useWhatsapp";

export function StickyCta() {
  const { url } = useWhatsapp();
  const reduceMotion = useReducedMotion();
  const [past, setPast] = useState(false);

  useEffect(() => {

    const onScroll = () => setPast(window.scrollY > 420);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!url) return null;

  return (
    <AnimatePresence>
      {past && (
        <motion.div
          initial={reduceMotion ? false : { y: 72 }}
          animate={{ y: 0 }}
          exit={reduceMotion ? undefined : { y: 72 }}
          transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          className="fixed inset-x-0 bottom-0 z-40 border-t border-sz-line bg-sz-panel/95 p-3 backdrop-blur-sm sm:hidden"
          style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
        >
          <a
            href={url}
            className="flex min-h-13 items-center justify-center gap-3 rounded-lg bg-sz-whatsapp px-5 text-[17px] font-semibold text-white"
          >
            <FaWhatsapp className="h-6 w-6" aria-hidden="true" />
            Message {BRAND}
          </a>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
