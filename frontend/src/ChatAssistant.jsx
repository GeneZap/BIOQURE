import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion as M } from "framer-motion";
import { MessageCircle, Send, Sparkles, X } from "lucide-react";

const WELCOME =
  "I'm the BIOQURE workspace assistant. Ask how to pick a dataset, run analysis, or what each report tab shows. I don't access patient data — answers are about this workspace only.";

const QUICK_PROMPTS = [
  "How do I run an analysis?",
  "What do the report tabs mean?",
  "Is this a diagnosis?",
];

function replyFor(text, ctx) {
  const q = text.toLowerCase().trim();
  if (!q) return "Type a question or tap a quick prompt below.";

  if (ctx.analyzing) {
    return "An analysis is running. When it finishes, the BIOQURE research report will appear below the dataset panel.";
  }

  if (/^(hi|hello|hey)\b/.test(q)) {
    return "Hello. I'm here to help you use this workspace — dataset selection, running analysis, and the report tabs. What would you like to know?";
  }

  if (/run|analy[sz]e|start|begin/.test(q)) {
    return "Select a dataset in the panel above, then click **Run BIOQURE Analysis**. The backend runs the classical and quantum models and returns a prediction, which populates the report below.";
  }

  if (/dataset|select|choose|pick|download/.test(q)) {
    return "Browse the curated public datasets (TCGA / GDC, RNA-seq expression). Selecting one loads its details; **Download Dataset** saves the underlying expression file for your own use.";
  }

  if (/overview/.test(q)) {
    return "**Overview** shows the model execution summary (selected model, prediction, confidence, quantum path) and the dataset context side by side.";
  }

  if (/benchmark/.test(q)) {
    return "**Benchmark** compares the classical models (Logistic Regression, RBF-SVM, XGBoost, MLP) and the quantum model on the same held-out metrics — accuracy, AUC, F1.";
  }

  if (/quantum|vqc|qubit|circuit/.test(q)) {
    return "**Quantum** shows the quantum circuit run for this sample: the encoded feature vector, the measurement outcomes, and whether the quantum path was used or the platform fell back to classical.";
  }

  if (/biomarker|gene|feature/.test(q)) {
    return "**Biomarkers** lists the 6–8 genes selected for this analysis, with their values and relative importance.";
  }

  if (/input|preprocess|metric/.test(q)) {
    return "**Input metrics** shows what BIOQURE detected in the uploaded or selected data before inference — sample counts, gene counts, and preprocessing notes.";
  }

  if (/api|backend|error|connect|failed|status/.test(q)) {
    return "If a request fails, the backend service may be unreachable or asleep. Check the connection status in the dataset panel, or try again in a few seconds.";
  }

  if (/diagnos|clinical|treatment|accurate|trust/.test(q)) {
    return "BIOQURE is a research decision-support interface using public datasets. Model predictions and biomarker signals are not a clinical diagnosis or treatment recommendation.";
  }

  if (ctx.hasResult && /result|done|complete|next/.test(q)) {
    return "You already have a report loaded. Explore the Overview, Benchmark, Quantum, Biomarkers, and Input metrics tabs, or pick another dataset above to run a new analysis.";
  }

  return "I can explain dataset selection, running analysis, and each report tab. Try rephrasing, or use a quick prompt. For clinical decisions, rely on qualified professionals — not this assistant.";
}

function formatReplyMarkdownish(s) {
  const parts = s.split(/\*\*(.+?)\*\*/g);
  return parts.map((chunk, i) =>
    i % 2 === 1 ? (
      <strong key={i} className="font-semibold text-[var(--bq-text)]">
        {chunk}
      </strong>
    ) : (
      <span key={i}>{chunk}</span>
    )
  );
}

export function ChatAssistant({ hasResult, analyzing }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState(() => [{ role: "assistant", text: WELCOME }]);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    if (open) scrollToBottom();
  }, [messages, open, scrollToBottom]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const send = useCallback(
    (raw) => {
      const text = typeof raw === "string" ? raw : input.trim();
      if (!text) return;
      setInput("");
      setMessages((m) => [...m, { role: "user", text }]);
      const ctx = { hasResult, analyzing };
      window.setTimeout(() => {
        const answer = replyFor(text, ctx);
        setMessages((m) => [...m, { role: "assistant", text: answer }]);
      }, 380);
    },
    [input, hasResult, analyzing]
  );

  const onSubmit = (e) => {
    e.preventDefault();
    send(input);
  };

  return (
    <div className="fixed bottom-5 right-5 z-[45] flex flex-col items-end gap-3 sm:bottom-6 sm:right-6">
      <AnimatePresence>
        {open && (
          <M.div
            key="panel"
            role="dialog"
            aria-label="BIOQURE assistant chat"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ type: "spring", stiffness: 420, damping: 32 }}
            className="flex w-[min(100vw-2rem,22rem)] flex-col overflow-hidden rounded-2xl border border-[var(--bq-border)] bg-[var(--bq-surface)] sm:w-[24rem]"
          >
            <div className="flex items-center justify-between border-b border-[var(--bq-border)] bg-[var(--bq-surface)] px-4 py-3">
              <div className="flex items-center gap-2.5">
                <div className="flex size-9 items-center justify-center rounded-xl border border-[var(--bq-accent)]/30 bg-[var(--bq-accent)]/10">
                  <Sparkles className="size-[18px] text-[var(--bq-accent)]" aria-hidden />
                </div>
                <div>
                  <p className="text-sm font-bold text-[var(--bq-text)]">Assistant</p>
                  <p className="text-[10px] text-[var(--bq-text-faint)]">Workspace help · not clinical advice</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg p-2 text-[var(--bq-text-faint)] transition-colors hover:bg-[var(--bq-surface-alt)] hover:text-[var(--bq-text)]"
                aria-label="Close assistant"
              >
                <X className="size-4" />
              </button>
            </div>

            <div role="log" aria-live="polite" className="max-h-[min(18rem,42vh)] space-y-3 overflow-y-auto px-3 py-3">
              {messages.map((msg, i) => (
                <div key={`${i}-${msg.role}`} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[92%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-[var(--bq-accent)] text-[#06201c]"
                        : "border border-[var(--bq-border)] bg-[var(--bq-surface-alt)] text-[var(--bq-text)]"
                    }`}
                  >
                    {msg.role === "assistant" ? formatReplyMarkdownish(msg.text) : msg.text}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            <div className="border-t border-[var(--bq-border)] px-3 py-2">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--bq-text-faint)]">Quick prompts</p>
              <div className="mb-3 flex flex-wrap gap-1.5">
                {QUICK_PROMPTS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => send(p)}
                    className="rounded-full border border-[var(--bq-border)] bg-[var(--bq-surface)] px-2.5 py-1 text-[11px] font-semibold text-[var(--bq-text-dim)] transition-colors hover:border-[var(--bq-accent)]/50 hover:bg-[var(--bq-accent)]/10"
                  >
                    {p}
                  </button>
                ))}
              </div>
              <form onSubmit={onSubmit} className="flex gap-2">
                <input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about this workspace…"
                  className="min-w-0 flex-1 rounded-xl border border-[var(--bq-border)] bg-[var(--bq-surface)] px-3 py-2.5 text-sm text-[var(--bq-text)] placeholder:text-[var(--bq-text-faint)] focus:border-[var(--bq-accent)]/60 focus:outline-none focus:ring-2 focus:ring-[var(--bq-accent)]/20"
                  autoComplete="off"
                />
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[var(--bq-accent)] text-[#06201c] transition-colors hover:bg-[var(--bq-accent-strong)] disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Send message"
                >
                  <Send className="size-4" />
                </button>
              </form>
            </div>
          </M.div>
        )}
      </AnimatePresence>

      <M.button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex size-14 items-center justify-center rounded-2xl bg-[var(--bq-accent)] text-[#06201c] transition-colors hover:bg-[var(--bq-accent-strong)]"
        aria-expanded={open}
        aria-label={open ? "Close assistant" : "Open BIOQURE assistant"}
      >
        {open ? <X className="size-6" aria-hidden /> : <MessageCircle className="size-6" aria-hidden />}
      </M.button>
    </div>
  );
}
