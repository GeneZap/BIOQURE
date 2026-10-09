import React, { useEffect, useRef, useState } from "react";
import { BookOpen, CircleHelp, Compass, LifeBuoy, RotateCcw } from "lucide-react";
import { contactSupport, openDocumentation, showTourWelcome, startProductTour } from "./tourEvents.js";

const SECTIONS = [
  {
    title: "Help Center",
    items: [
      { label: "Take Product Tour", hint: "8-step walkthrough", icon: Compass, action: startProductTour },
      { label: "View Documentation", hint: "Guides & API reference", icon: BookOpen, action: openDocumentation },
    ],
  },
  {
    title: "Support",
    items: [
      { label: "Restart onboarding guide", hint: "Show the welcome screen", icon: RotateCcw, action: showTourWelcome },
      { label: "Contact support", hint: "Get help from the team", icon: LifeBuoy, action: contactSupport },
    ],
  },
];

export default function HelpMenu() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => {
      if (!rootRef.current?.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative" data-tour="help-menu">
      <button
        type="button"
        className="bq-icon-btn"
        aria-label="Help and support"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <CircleHelp className="size-4" aria-hidden />
      </button>

      {open && (
        <div role="menu" className="bq-help-menu bq-hud absolute right-0 top-[calc(100%+10px)] z-50 w-72 p-2">
          {SECTIONS.map((section) => (
            <div key={section.title} className="py-1">
              <div className="bq-panel-title px-2 pb-1.5 pt-1 text-[10px]">{section.title}</div>
              {section.items.map(({ label, hint, icon: Icon, action }) => (
                <button
                  key={label}
                  type="button"
                  role="menuitem"
                  className="bq-help-item"
                  onClick={() => {
                    setOpen(false);
                    action();
                  }}
                >
                  <span className="bq-help-icon">
                    {React.createElement(Icon, {
                      className: "size-4",
                      "aria-hidden": true,
                    })}
                  </span>
                  <span className="min-w-0 text-left">
                    <span className="block text-[13px] font-medium text-[var(--bq-text)]">{label}</span>
                    <span className="block text-[11px] text-[var(--bq-text-faint)]">{hint}</span>
                  </span>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
