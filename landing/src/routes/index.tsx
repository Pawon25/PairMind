import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "PairMind — Two agents negotiate a procurement deal" },
      {
        name: "description",
        content:
          "PairMind runs a Buyer and a Seller agent through a structured, document-grounded negotiation over price, delivery, payment terms and warranty — turn by turn, until agreement or walk-away.",
      },
      { property: "og:title", content: "PairMind — Two agents negotiate a procurement deal" },
      {
        property: "og:description",
        content:
          "A Buyer and a Seller agent negotiate a B2B procurement deal in structured, citation-grounded turns. Built on LangGraph, OpenSearch hybrid retrieval, and Claude Haiku.",
      },
    ],
  }),
  component: Index,
});

/* ------------------------------- data ------------------------------- */

type Side = "buyer" | "seller";
type MsgType = "PROPOSE" | "COUNTER" | "ACCEPT" | "WALK_AWAY";

interface Turn {
  n: number;
  side: Side;
  type: MsgType;
  unit: number;
  changed: string;
  rationale: string;
  cite: string;
}

const TURNS: Turn[] = [
  {
    n: 1,
    side: "buyer",
    type: "PROPOSE",
    unit: 500,
    changed: "unit_price = $500 · net_60 · 24mo warranty",
    rationale: "Opening anchor below market median; budget ceiling at $520.",
    cite: "RFP-04",
  },
  {
    n: 2,
    side: "seller",
    type: "COUNTER",
    unit: 535,
    changed: "unit_price = $535 · net_30 · 18mo warranty",
    rationale: "Floor is $508; opening above to leave room on payment terms.",
    cite: "PL-22",
  },
  {
    n: 3,
    side: "buyer",
    type: "COUNTER",
    unit: 510,
    changed: "unit_price = $510 · net_45 · 24mo warranty",
    rationale: "Concede on payment window in exchange for price movement.",
    cite: "RFP-11",
  },
  {
    n: 4,
    side: "seller",
    type: "COUNTER",
    unit: 528,
    changed: "unit_price = $528 · net_45 · 24mo warranty",
    rationale: "Warranty extension acceptable per service-cost model.",
    cite: "QA-07",
  },
  {
    n: 5,
    side: "buyer",
    type: "COUNTER",
    unit: 520,
    changed: "unit_price = $520 · net_45 · 24mo warranty",
    rationale: "Matches authorized ceiling; final movement before walk.",
    cite: "RFP-04",
  },
  {
    n: 6,
    side: "seller",
    type: "COUNTER",
    unit: 515,
    changed: "unit_price = $515 · net_45 · 24mo warranty",
    rationale: "Within margin floor when amortized over 24-month volume.",
    cite: "PL-22",
  },
  {
    n: 7,
    side: "buyer",
    type: "ACCEPT",
    unit: 515,
    changed: "AGREEMENT — $515 · net_45 · 24mo warranty",
    rationale: "All authorized terms satisfied. Closing the deal.",
    cite: "RFP-04",
  },
];

/* ------------------------------- page ------------------------------- */

function Index() {
  const [demoOpen, setDemoOpen] = useState(false);
  const [gateOpen, setGateOpen] = useState(false);
  const [gateNotice, setGateNotice] = useState<string | null>(null);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("expired")) {
      setGateNotice("Your access expired or reached its usage limit — enter a new token to continue.");
      setGateOpen(true);
    }
  }, []);

  return (
    <div className="paper-grain relative min-h-screen text-ink">
      <ParallaxSheets />
      <div className="relative z-10">
        <Nav onRequestDemo={() => setDemoOpen(true)} onEnterToken={() => setGateOpen(true)} />
        <Hero />
        <Ledger />
        <HowItWorks />
        <Isolation />
        <Outcomes />
        <Stack />
        <Footer onRequestDemo={() => setDemoOpen(true)} />
        <RequestDemoModal open={demoOpen} onClose={() => setDemoOpen(false)} />
        <TokenGateModal open={gateOpen} onClose={() => setGateOpen(false)} notice={gateNotice} />
      </div>
    </div>
  );
}

/* --------------------------- parallax sheets --------------------------- */

function ParallaxSheets() {
  const [y, setY] = useState(0);
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setEnabled(!mq.matches);
    apply();
    mq.addEventListener?.("change", apply);
    return () => mq.removeEventListener?.("change", apply);
  }, []);

  useEffect(() => {
    if (!enabled) {
      setY(0);
      return;
    }
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        setY(window.scrollY);
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [enabled]);

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div
        className="absolute -left-[2%] right-[8%] -top-[4%] h-[130vh] border border-ink/[0.05] bg-[var(--paper-2)]/50 will-change-transform"
        style={{ transform: `translate3d(0, ${y * -0.04}px, 0) rotate(-0.5deg)` }}
      />
      <div
        className="absolute left-[6%] -right-[2%] -top-[2%] h-[130vh] border border-ink/[0.06] bg-[var(--paper-2)]/40 will-change-transform"
        style={{ transform: `translate3d(0, ${y * -0.08}px, 0) rotate(0.4deg)` }}
      />
      <div
        className="absolute left-[3%] right-[3%] top-[1%] h-[130vh] border border-ink/[0.04] will-change-transform"
        style={{ transform: `translate3d(0, ${y * -0.12}px, 0) rotate(-0.15deg)` }}
      />
    </div>
  );
}

/* ------------------------------- nav -------------------------------- */

function Nav({ onRequestDemo, onEnterToken }: { onRequestDemo: () => void; onEnterToken: () => void }) {
  return (
    <header className="border-b border-rule/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <a href="#top" className="flex items-center gap-3">
          <Mark />
          <span className="font-display text-lg font-600 tracking-tight">PairMind</span>
        </a>
        <nav className="hidden gap-8 font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft sm:flex">
          <a href="#ledger" className="hover:text-ink">Ledger</a>
          <a href="#protocol" className="hover:text-ink">Protocol</a>
          <a href="#isolation" className="hover:text-ink">Isolation</a>
          <a href="#outcomes" className="hover:text-ink">Outcomes</a>
        </nav>
        <div className="flex items-center gap-5">
          <button
            type="button"
            onClick={onEnterToken}
            className="border-0 bg-transparent p-0 font-mono text-[11px] uppercase tracking-[0.18em] underline decoration-brass decoration-2 underline-offset-4 hover:text-emerald-deal"
          >
            Have a token?
          </button>
          <button
            type="button"
            onClick={onRequestDemo}
            className="border-0 bg-transparent p-0 font-mono text-[11px] uppercase tracking-[0.18em] underline decoration-brass decoration-2 underline-offset-4 hover:text-emerald-deal"
          >
            Request Demo
          </button>
        </div>
      </div>
    </header>
  );
}

function Mark() {
  return (
    <span aria-hidden className="inline-flex h-7 w-7 items-center justify-center border-2 border-ink">
      <span className="block h-3 w-[2px] bg-emerald-deal" />
      <span className="mx-[2px] block h-1 w-1 rounded-full bg-brass" />
      <span className="block h-3 w-[2px] bg-rust-deal" />
    </span>
  );
}

/* ------------------------------- hero ------------------------------- */

function Hero() {
  return (
    <section id="top" className="border-b border-rule/80">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-10 px-6 pb-16 pt-20 md:grid-cols-12 md:pb-24 md:pt-28">
        <div className="md:col-span-7">
          <div className="mb-8 flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.22em] text-ink-soft">
            <span className="h-px w-8 bg-ink" />
            <span>Deal Memo · v0.1 · two-party autonomous negotiation</span>
          </div>
          <h1 className="font-display text-[44px] leading-[1.05] tracking-[-0.015em] sm:text-[58px] md:text-[68px]">
            Two agents sit down,<br />
            <span className="text-emerald-deal">open the documents,</span><br />
            and <span className="text-rust-deal">work out the deal.</span>
          </h1>
          <p className="mt-7 max-w-xl text-[17px] leading-relaxed text-ink-soft">
            PairMind runs a Buyer and a Seller as separate agents. They negotiate
            <span className="text-ink"> unit price, delivery, payment terms and warranty </span>
            across multiple turns — each move grounded in citations from their own
            private documents — until they reach agreement or walk away.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-3 font-mono text-[12px] text-ink-soft">
            <KV k="orchestration" v="LangGraph" />
            <KV k="retrieval" v="OpenSearch · BM25+kNN+RRF" />
            <KV k="reasoning" v="Claude Haiku" />
            <KV k="transport" v="SSE → React" />
          </div>
        </div>

        <aside className="md:col-span-5">
          <DealHeaderCard />
        </aside>
      </div>
    </section>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <span className="flex items-baseline gap-2">
      <span className="text-[10px] uppercase tracking-[0.18em] text-ink-soft/70">{k}</span>
      <span className="text-ink">{v}</span>
    </span>
  );
}

function DealHeaderCard() {
  const cardRef = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState<{ rx: number; ry: number; active: boolean }>({
    rx: 0,
    ry: 0,
    active: false,
  });
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setEnabled(!reduce.matches);
    apply();
    reduce.addEventListener?.("change", apply);
    return () => {
      reduce.removeEventListener?.("change", apply);
    };
  }, []);

  const onMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!enabled) return;
    const el = cardRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    const nx = (e.clientX - r.left) / r.width - 0.5;
    const ny = (e.clientY - r.top) / r.height - 0.5;
    const max = 5;
    setTilt({
      rx: Math.max(-max, Math.min(max, -ny * 2 * max)),
      ry: Math.max(-max, Math.min(max, nx * 2 * max)),
      active: true,
    });
  };
  const onLeave = () => setTilt({ rx: 0, ry: 0, active: false });

  const shadowX = -tilt.ry * 1.6;
  const shadowY = 8 + tilt.rx * 1.6;

  return (
    <div style={{ perspective: "900px" }}>
      <div
        ref={cardRef}
        onPointerMove={onMove}
        onPointerLeave={onLeave}
        className="relative border-2 border-ink bg-paper will-change-transform"
        style={{
          transform: `rotateX(${tilt.rx}deg) rotateY(${tilt.ry}deg)`,
          transformOrigin: "center center",
          transition: tilt.active
            ? "transform 80ms linear, box-shadow 80ms linear"
            : "transform 400ms cubic-bezier(0.2,0.8,0.2,1), box-shadow 400ms ease",
          boxShadow: enabled
            ? `${shadowX}px ${shadowY}px ${18 + Math.abs(tilt.rx + tilt.ry)}px -6px oklch(0.22 0.008 145 / 0.18)`
            : undefined,
          transformStyle: "preserve-3d",
        }}
      >
        <div className="flex items-center justify-between border-b-2 border-ink bg-ink px-4 py-2 font-mono text-[10px] uppercase tracking-[0.22em] text-paper">
          <span>Deal · PM-2041</span>
          <span>session.open</span>
        </div>
        <dl className="grid grid-cols-2 divide-x divide-rule">
          <div className="p-4">
            <dt className="font-mono text-[10px] uppercase tracking-[0.2em] text-emerald-deal">Buyer</dt>
            <dd className="mt-1 font-display text-xl">Orion Manufacturing</dd>
            <dd className="mt-2 font-mono text-[11px] text-ink-soft">qty: 1,200 units</dd>
            <dd className="font-mono text-[11px] text-ink-soft">ceiling: $520 / unit</dd>
          </div>
          <div className="p-4">
            <dt className="font-mono text-[10px] uppercase tracking-[0.2em] text-rust-deal">Seller</dt>
            <dd className="mt-1 font-display text-xl">Halden Components Co.</dd>
            <dd className="mt-2 font-mono text-[11px] text-ink-soft">sku: HC-44A</dd>
            <dd className="font-mono text-[11px] text-ink-soft">floor: $508 / unit</dd>
          </div>
        </dl>
        <div className="border-t-2 border-dashed border-ink px-4 py-3 font-mono text-[11px] text-ink-soft">
          <div className="flex items-center justify-between">
            <span>turn_limit = 12</span>
            <span>citations = required</span>
          </div>
        </div>
        <div className="absolute -right-3 -top-3 h-6 w-6 rotate-12 bg-brass" aria-hidden />
      </div>
    </div>
  );
}

/* ----------------------------- ledger ------------------------------- */

function Ledger() {
  const [reduceMotion, setReduceMotion] = useState(false);
  const [latestRevealed, setLatestRevealed] = useState(-1);
  const [tapePrice, setTapePrice] = useState<number | null>(null);
  const [resetKey, setResetKey] = useState(0);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReduceMotion(mq.matches);
    apply();
    mq.addEventListener?.("change", apply);
    return () => mq.removeEventListener?.("change", apply);
  }, []);

  // Reduced motion: snap everything to final state immediately.
  useEffect(() => {
    if (reduceMotion) {
      setLatestRevealed(TURNS.length - 1);
      setTapePrice(TURNS[TURNS.length - 1].unit);
    }
  }, [reduceMotion]);

  // Section-aware reset: when the whole § 01 section scrolls past above the
  // viewport, snap all turn state back to hidden so the reveal replays on
  // the next downward entry.
  useEffect(() => {
    if (reduceMotion) return;
    const el = sectionRef.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (!e.isIntersecting && e.boundingClientRect.bottom < 0) {
            setLatestRevealed(-1);
            setTapePrice(null);
            setResetKey((k) => k + 1);
          }
        }
      },
      { threshold: 0 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [reduceMotion]);

  // Tape count-up: each time a higher-indexed turn reveals, animate
  // from the currently displayed price to that turn's unit price.
  useEffect(() => {
    if (latestRevealed < 0) return;
    const target = TURNS[latestRevealed].unit;
    if (reduceMotion) {
      setTapePrice(target);
      return;
    }
    const from =
      tapePrice ?? (latestRevealed > 0 ? TURNS[latestRevealed - 1].unit : 0);
    if (from === target) {
      setTapePrice(target);
      return;
    }
    const duration = 550;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const k = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - k, 2);
      setTapePrice(Math.round(from + (target - from) * eased));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      if (raf) cancelAnimationFrame(raf);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latestRevealed, reduceMotion]);

  const handleReveal = useCallback(
    (i: number) => setLatestRevealed((prev) => (i > prev ? i : prev)),
    []
  );

  const sealed = latestRevealed >= TURNS.length - 1;

  return (
    <section ref={sectionRef} id="ledger" className="border-b border-rule/80">
      <div className="mx-auto max-w-6xl px-6 py-16 md:py-24">
        <SectionLabel n="01" title="The Ledger" />

        {/* Price tape — pins to top of viewport while inside the Ledger section,
            un-pins automatically once its containing block scrolls past. */}
        <div className="sticky top-0 z-20 mb-12 flex flex-wrap items-end justify-between gap-6 border-y-2 border-ink bg-paper py-5">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-soft">
              unit_price · running ledger total
            </div>
            <div className="mt-1 flex items-baseline gap-3 font-mono">
              <span className="font-display text-5xl tabular-nums">
                ${tapePrice ?? "—"}
              </span>
              <span className="text-xs text-ink-soft">/ unit · USD</span>
            </div>
          </div>
          {sealed && (
            <div className={`${reduceMotion ? "" : "animate-seal-in"} stamp text-emerald-deal`}>
              <BrassDot /> Agreement · turn 07
            </div>
          )}
        </div>

        <ol className="space-y-6 md:space-y-10">
          {TURNS.map((t, idx) => (
            <TurnRow
              key={t.n}
              t={t}
              idx={idx}
              prevUnit={idx > 0 ? TURNS[idx - 1].unit : 0}
              reduceMotion={reduceMotion}
              onReveal={handleReveal}
              resetKey={resetKey}
            />
          ))}
        </ol>
      </div>
    </section>
  );
}

function TurnRow({
  t,
  idx,
  prevUnit,
  reduceMotion,
  onReveal,
  resetKey,
}: {
  t: Turn;
  idx: number;
  prevUnit: number;
  reduceMotion: boolean;
  onReveal: (i: number) => void;
  resetKey: number;
}) {
  const liRef = useRef<HTMLLIElement>(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    if (reduceMotion) {
      setRevealed(true);
      onReveal(idx);
      return;
    }
    setRevealed(false);
    const el = liRef.current;
    if (!el) return;

    let raf = 0;
    let io: IntersectionObserver | null = null;

    raf = requestAnimationFrame(() => {
      io = new IntersectionObserver(
        (entries) => {
          for (const e of entries) {
            if (e.isIntersecting) {
              setRevealed(true);
              onReveal(idx);
              io?.disconnect();
              break;
            }
          }
        },
        { rootMargin: "0px 0px -12% 0px", threshold: 0.18 },
      );
      io.observe(el);
    });

    return () => {
      cancelAnimationFrame(raf);
      io?.disconnect();
    };
  }, [idx, reduceMotion, onReveal, resetKey]);

  const isBuyer = t.side === "buyer";
  return (
    <li ref={liRef} className="grid grid-cols-1 items-stretch md:grid-cols-2">
      {isBuyer ? (
        <>
          <div className="md:pr-10">
            <TurnCard t={t} prevUnit={prevUnit} revealed={revealed} reduceMotion={reduceMotion} />
          </div>
          <div className="hidden md:block" />
        </>
      ) : (
        <>
          <div className="hidden md:block" />
          <div className="md:pl-10">
            <TurnCard t={t} prevUnit={prevUnit} revealed={revealed} reduceMotion={reduceMotion} />
          </div>
        </>
      )}
    </li>
  );
}

function TurnCard({
  t,
  prevUnit,
  revealed,
  reduceMotion,
}: {
  t: Turn;
  prevUnit: number;
  revealed: boolean;
  reduceMotion: boolean;
}) {
  const isBuyer = t.side === "buyer";
  const tone = isBuyer ? "text-emerald-deal" : "text-rust-deal";
  const borderTone = isBuyer ? "border-emerald-deal" : "border-rust-deal";
  const align = isBuyer ? "md:text-right md:items-end" : "md:text-left md:items-start";
  const sideSign = isBuyer ? 1 : -1;

  // Price count-up on reveal: prevUnit → t.unit.
  const [price, setPrice] = useState<number>(reduceMotion ? t.unit : prevUnit);
  useEffect(() => {
    if (reduceMotion) {
      setPrice(t.unit);
      return;
    }
    if (!revealed) {
      setPrice(prevUnit);
      return;
    }
    const from = prevUnit;
    const to = t.unit;
    if (from === to) {
      setPrice(to);
      return;
    }
    const duration = 550;
    let raf = 0;
    let start = 0;
    const tick = (now: number) => {
      if (!start) start = now;
      const k = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - k, 2);
      setPrice(Math.round(from + (to - from) * eased));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    // align with stagger slot 1 (price line)
    const delay = window.setTimeout(() => {
      raf = requestAnimationFrame(tick);
    }, 80);
    return () => {
      window.clearTimeout(delay);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [revealed, reduceMotion, prevUnit, t.unit]);

  const slot = (i: number): React.CSSProperties =>
    reduceMotion
      ? {}
      : {
          opacity: revealed ? 1 : 0,
          transform: revealed ? "translateY(0)" : "translateY(18px)",
          transition: "opacity 450ms ease-out, transform 450ms ease-out",
          transitionDelay: `${i * 80}ms`,
          willChange: "opacity, transform",
        };

  // Stamp tilt-in: starts tilted, settles flat — timed to stamp's stagger slot.
  const stampStyle: React.CSSProperties = reduceMotion
    ? {}
    : {
        transform: revealed
          ? "rotateX(0deg) rotateY(0deg)"
          : `rotateX(6deg) rotateY(${sideSign * 7}deg)`,
        transition: "transform 500ms ease-out",
        transitionDelay: `${3 * 80}ms`,
        transformOrigin: "center center",
        transformStyle: "preserve-3d",
      };

  // Split `changed` so the $unit numeral can animate inline.
  const priceToken = `$${t.unit}`;
  const splitIdx = t.changed.indexOf(priceToken);
  const before = splitIdx >= 0 ? t.changed.slice(0, splitIdx) : t.changed;
  const after =
    splitIdx >= 0 ? t.changed.slice(splitIdx + priceToken.length) : "";

  return (
    <article
      className={`group relative flex flex-col gap-3 border-l-4 ${borderTone} bg-paper p-5 transition-transform duration-200 hover:-translate-y-[2px] focus-within:-translate-y-[2px] md:border-l-0 ${
        isBuyer ? "md:border-r-4" : "md:border-l-4"
      } ${borderTone}`}
      tabIndex={0}
    >
      <header
        className={`flex items-center gap-3 ${align} md:justify-end ${!isBuyer ? "md:justify-start md:flex-row" : "md:flex-row-reverse"}`}
        style={slot(0)}
      >
        <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
          turn_{String(t.n).padStart(2, "0")}
        </span>
        <span className={`font-mono text-[11px] uppercase tracking-[0.18em] ${tone}`}>
          {isBuyer ? "buyer →" : "← seller"}
        </span>
        <span className={`stamp !rotate-0 !border ${tone} !px-2 !py-[2px] !text-[10px]`}>
          {t.type.replace("_", " ")}
        </span>
      </header>

      <div className={`font-mono text-[13px] text-ink ${align}`} style={slot(1)}>
        {splitIdx >= 0 ? (
          <>
            {before}
            <span className="tabular-nums">${price}</span>
            {after}
          </>
        ) : (
          t.changed
        )}
      </div>

      <p className={`text-[14px] leading-relaxed text-ink-soft ${align}`} style={slot(2)}>
        {t.rationale}
      </p>

      <footer
        className={`flex items-center gap-2 ${isBuyer ? "md:justify-end" : "md:justify-start"}`}
        style={slot(3)}
      >
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-soft">
          cite
        </span>
        <span className="inline-block" style={{ perspective: "320px" }}>
          <span className="wax-seal" title={`Citation: ${t.cite}`} style={stampStyle}>
            {t.cite.split("-")[0]}
          </span>
        </span>
        <span className="font-mono text-[10px] text-ink-soft">§ {t.cite}</span>
      </footer>
    </article>
  );
}

/* --------------------------- how it works --------------------------- */

const STEPS = [
  {
    k: "retrieve",
    title: "Retrieve",
    body:
      "Hybrid search over each agent's private corpus — BM25 + kNN, fused with Reciprocal Rank. Tag filters keep buyer docs out of the seller's index, and vice versa.",
  },
  {
    k: "reason",
    title: "Reason",
    body:
      "Claude Haiku is called with the retrieved passages and prior turn history. The model must emit a strict JSON envelope: msg_type, terms, rationale, citations.",
  },
  {
    k: "validate",
    title: "Validate",
    body:
      "Every cited passage is checked against the retrieval set. One automatic retry on schema or citation failure — then the turn is rejected.",
  },
  {
    k: "decide",
    title: "Decide",
    body:
      "The validated envelope routes the LangGraph state machine to PROPOSE, COUNTER, ACCEPT or WALK_AWAY. The other agent picks up the next turn.",
  },
  {
    k: "loop",
    title: "Loop",
    body:
      "Repeat until acceptance, walk-away, deadlock detection (two identical offers in a row), or the turn limit is reached. Every transition streams to the UI over SSE.",
  },
];

function HowItWorks() {
  return (
    <section id="protocol" className="border-b border-rule/80">
      <div className="mx-auto max-w-6xl px-6 py-20 md:py-28">
        <SectionLabel n="02" title="Protocol" />
        <h2 className="mt-2 max-w-3xl font-display text-3xl leading-tight md:text-4xl">
          One loop, five disciplined steps. No free-form chat.
        </h2>
        <ol className="mt-12 grid grid-cols-1 gap-px overflow-hidden border border-ink bg-ink md:grid-cols-5">
          {STEPS.map((s, i) => (
            <li key={s.k} className="flex flex-col gap-3 bg-paper p-5">
              <div className="flex items-baseline justify-between font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
                <span>step_{String(i + 1).padStart(2, "0")}</span>
                <span className="text-brass">●</span>
              </div>
              <h3 className="font-display text-xl">{s.title}</h3>
              <p className="text-[13.5px] leading-relaxed text-ink-soft">{s.body}</p>
              <code className="mt-auto pt-2 font-mono text-[11px] text-emerald-deal">
                .{s.k}()
              </code>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* ---------------------------- isolation ----------------------------- */

function Isolation() {
  return (
    <section id="isolation" className="border-b border-rule/80">
      <div className="mx-auto max-w-6xl px-6 py-20 md:py-28">
        <SectionLabel n="03" title="Agent Isolation" />
        <h2 className="mt-2 max-w-3xl font-display text-3xl leading-tight md:text-4xl">
          Neither agent ever reads the other's brief.
        </h2>
        <p className="mt-4 max-w-2xl text-ink-soft">
          The Buyer and Seller graphs share only the public turn log. System prompts,
          retrieval indexes, and authority limits are partitioned at the orchestration
          layer — not just by convention.
        </p>

        <div className="relative mt-12 grid grid-cols-1 gap-4 md:grid-cols-[1fr_auto_1fr]">
          <PrivateBox
            side="buyer"
            label="Buyer · Orion Manufacturing"
            items={[
              { k: "budget_ceiling", v: "$520 / unit" },
              { k: "min_warranty", v: "24 months" },
              { k: "payment_window", v: "net_45 or longer" },
              { k: "walk_conditions", v: "delivery > 6 weeks" },
              { k: "docs", v: "RFP-04, RFP-11, SOW-09" },
            ]}
          />

          {/* Sealed divider */}
          <div className="flex items-center justify-center md:flex-col md:py-6">
            <SealDivider />
          </div>

          <PrivateBox
            side="seller"
            label="Seller · Halden Components"
            items={[
              { k: "margin_floor", v: "$508 / unit" },
              { k: "max_warranty", v: "30 months" },
              { k: "preferred_terms", v: "net_30" },
              { k: "lead_time", v: "4 weeks at current volume" },
              { k: "docs", v: "PL-22, QA-07, MFG-13" },
            ]}
          />
        </div>
      </div>
    </section>
  );
}

function PrivateBox({
  side,
  label,
  items,
}: {
  side: Side;
  label: string;
  items: { k: string; v: string }[];
}) {
  const tone = side === "buyer" ? "text-emerald-deal" : "text-rust-deal";
  const borderTone = side === "buyer" ? "border-emerald-deal" : "border-rust-deal";
  return (
    <div className={`border-2 ${borderTone} bg-paper`}>
      <div className={`flex items-center justify-between border-b-2 ${borderTone} px-4 py-2`}>
        <span className={`font-mono text-[10px] uppercase tracking-[0.22em] ${tone}`}>
          {label}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-soft">
          private · sealed
        </span>
      </div>
      <dl className="divide-y divide-rule">
        {items.map((it) => (
          <div key={it.k} className="grid grid-cols-[140px_1fr] gap-4 px-4 py-2.5 font-mono text-[12px]">
            <dt className="text-ink-soft">{it.k}</dt>
            <dd className="text-ink">{it.v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function SealDivider() {
  return (
    <div className="flex items-center gap-2 md:flex-col" aria-hidden>
      <div className="h-px w-10 bg-ink md:h-10 md:w-px" />
      <div className="wax-seal !h-10 !w-10 !text-[10px]">SEAL</div>
      <div className="h-px w-10 bg-ink md:h-10 md:w-px" />
    </div>
  );
}

/* ----------------------------- outcomes ----------------------------- */

const OUTCOMES: { label: string; tone: string; desc: string }[] = [
  {
    label: "AGREEMENT",
    tone: "text-emerald-deal",
    desc: "Both agents emit ACCEPT on identical terms. The deal envelope is sealed and returned.",
  },
  {
    label: "WALK_AWAY",
    tone: "text-rust-deal",
    desc: "One side determines no in-policy move exists. Reasons are logged with citations.",
  },
  {
    label: "DEADLOCK",
    tone: "text-ink",
    desc: "Two consecutive identical offers detected. The loop halts before burning the turn budget.",
  },
  {
    label: "TIMEOUT",
    tone: "text-brass",
    desc: "The turn_limit was reached without convergence. State is preserved for human review.",
  },
];

function Outcomes() {
  return (
    <section id="outcomes" className="border-b border-rule/80">
      <div className="mx-auto max-w-6xl px-6 py-20 md:py-28">
        <SectionLabel n="04" title="Termination" />
        <h2 className="mt-2 max-w-3xl font-display text-3xl leading-tight md:text-4xl">
          A session ends in exactly one of four states.
        </h2>
        <div className="mt-12 grid grid-cols-2 gap-6 md:grid-cols-4">
          {OUTCOMES.map((o) => (
            <div key={o.label} className="flex flex-col items-start gap-4">
              <span className={`stamp ${o.tone}`}>
                <BrassDot /> {o.label}
              </span>
              <p className="text-[13.5px] leading-relaxed text-ink-soft">{o.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function BrassDot() {
  return <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full bg-brass" />;
}

/* ------------------------------ stack ------------------------------- */

function Stack() {
  const items = ["LangGraph", "OpenSearch", "Claude Haiku", "FastAPI", "React", "SSE"];
  return (
    <section className="border-b border-rule/80">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6 px-6 py-8 font-mono text-[12px] uppercase tracking-[0.18em] text-ink-soft">
        <span className="text-ink">// stack</span>
        <ul className="flex flex-wrap items-center gap-x-5 gap-y-2">
          {items.map((i, idx) => (
            <li key={i} className="flex items-center gap-5">
              <span>{i}</span>
              {idx < items.length - 1 && <span className="text-brass">·</span>}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ------------------------------ footer ------------------------------ */

function Footer({ onRequestDemo }: { onRequestDemo: () => void }) {
  return (
    <footer>
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 px-6 py-14 md:grid-cols-2">
        <div>
          <h3 className="font-display text-2xl">Open the session.</h3>
          <p className="mt-2 max-w-md text-ink-soft">
            Clone the repo, drop your own deal documents into the buyer and seller
            corpora, and watch the ledger fill in turn by turn.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={onRequestDemo}
              className="inline-flex items-center gap-2 border-2 border-ink bg-ink px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] text-paper hover:bg-emerald-deal hover:border-emerald-deal"
            >
              Request Demo
            </button>
            <a
              href="#protocol"
              className="inline-flex items-center gap-2 border-2 border-ink px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] hover:text-emerald-deal"
            >
              Read the protocol
            </a>
            <a
              href="https://github.com/Pawon25/PairMind"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 border-2 border-ink px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] hover:text-emerald-deal"
            >
              View on GitHub
            </a>
          </div>
        </div>
        <div className="flex flex-col items-start gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft md:items-end">
          <div className="flex items-center gap-2">
            <span className="wax-seal !h-6 !w-6 !text-[9px]">PM</span>
            <span>PairMind · v0.1</span>
          </div>
          <a
            href="https://pavanb.in/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 group"
          >
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft group-hover:text-ink transition-colors">
              Built by
            </span>
            <span className="stamp text-ink group-hover:text-emerald-deal group-hover:border-emerald-deal transition-colors">
              <BrassDot /> Pavan B
            </span>
          </a>
          <span>© {new Date().getFullYear()} — All terms negotiable.</span>
        </div>
      </div>
    </footer>
  );
}

/* -------------------------- request demo modal -------------------------- */

function RequestDemoModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/demo-request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, message }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.detail || "Could not send your request. Try emailing directly instead.");
        setSubmitting(false);
        return;
      }
      setSent(true);
    } catch {
      setError("Could not reach the server. Try emailing directly instead.");
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="relative w-full max-w-lg border-2 border-ink bg-paper p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="demo-heading"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 font-mono text-[18px] leading-none text-ink-soft hover:text-ink"
          aria-label="Close"
        >
          ×
        </button>
        <h2 id="demo-heading" className="font-display text-2xl">
          Request the live demo
        </h2>
        <p className="mt-2 text-[14px] leading-relaxed text-ink-soft">
          PairMind's live negotiation runs real Claude Haiku calls per session, so I review
          requests individually to keep it sustainable. Tell me a bit about what you'd like to see.
        </p>
        {sent ? (
          <p className="mt-5 border-2 border-emerald-deal bg-emerald-deal/10 px-3 py-3 text-[14px] leading-relaxed text-ink">
            Request received — I'll follow up by email with a token if it's a good fit.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <div>
              <label htmlFor="demo-name" className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
                Name
              </label>
              <input
                id="demo-name"
                type="text"
                required
                placeholder="Jane Cooper"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full border-2 border-ink bg-paper px-3 py-2 font-sans text-[14px] text-ink placeholder:text-ink-soft/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink"
              />
            </div>
            <div>
              <label htmlFor="demo-email" className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
                Email
              </label>
              <input
                id="demo-email"
                type="email"
                required
                placeholder="jane@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full border-2 border-ink bg-paper px-3 py-2 font-sans text-[14px] text-ink placeholder:text-ink-soft/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink"
              />
            </div>
            <div>
              <label htmlFor="demo-message" className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
                What are you exploring this for?
              </label>
              <textarea
                id="demo-message"
                placeholder="e.g. evaluating for a hiring process, curious about the agent architecture, considering it for a similar use case..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={4}
                className="mt-1 w-full resize-none border-2 border-ink bg-paper px-3 py-2 font-sans text-[14px] text-ink placeholder:text-ink-soft/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink"
              />
            </div>
            {error && (
              <p className="text-[13px] leading-relaxed text-rust-deal">{error}</p>
            )}
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 border-2 border-ink bg-ink px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] text-paper hover:bg-emerald-deal hover:border-emerald-deal disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? "Sending…" : "Send request"}
            </button>
          </form>
        )}
        <p className="mt-4 font-mono text-[11px] text-ink-soft">
          Or email directly:{" "}
          <a
            href="mailto:pavanbasavaraj25@gmail.com"
            className="text-ink underline decoration-brass decoration-2 underline-offset-4"
          >
            pavanbasavaraj25@gmail.com
          </a>
        </p>
      </div>
    </div>
  );
}

function TokenGateModal({
  open,
  onClose,
  notice,
}: {
  open: boolean;
  onClose: () => void;
  notice: string | null;
}) {
  const [token, setToken] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/verify-token", {
        method: "POST",
        headers: { Authorization: `Bearer ${token.trim()}` },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.detail || "Could not verify token.");
        setSubmitting(false);
        return;
      }
      // Key must match ACCESS_TOKEN_KEY in frontend/src/api/index.js - same
      // origin behind Nginx, so sessionStorage is shared between / and /app.
      sessionStorage.setItem("pm_access_token", token.trim());
      window.location.href = "/app";
    } catch {
      setError("Could not reach the server. Try again in a moment.");
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="relative w-full max-w-md border-2 border-ink bg-paper p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="gate-heading"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 font-mono text-[18px] leading-none text-ink-soft hover:text-ink"
          aria-label="Close"
        >
          ×
        </button>
        <h2 id="gate-heading" className="font-display text-2xl">
          Enter your access token
        </h2>
        <p className="mt-2 text-[14px] leading-relaxed text-ink-soft">
          Access is invite-only - if you don't have a token yet, use "Request Demo" instead.
        </p>
        {notice && (
          <p className="mt-3 border-2 border-brass bg-brass/10 px-3 py-2 text-[13px] leading-relaxed text-ink">
            {notice}
          </p>
        )}
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label htmlFor="gate-token" className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
              Token
            </label>
            <input
              id="gate-token"
              type="text"
              required
              autoFocus
              placeholder="Paste your token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className="mt-1 w-full border-2 border-ink bg-paper px-3 py-2 font-mono text-[13px] text-ink placeholder:text-ink-soft/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink"
            />
          </div>
          {error && (
            <p className="text-[13px] leading-relaxed text-rust-deal">{error}</p>
          )}
          <button
            type="submit"
            disabled={submitting || !token.trim()}
            className="inline-flex items-center gap-2 border-2 border-ink bg-ink px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] text-paper hover:bg-emerald-deal hover:border-emerald-deal disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Verifying…" : "Enter"}
          </button>
        </form>
      </div>
    </div>
  );
}

/* ------------------------------ shared ------------------------------ */

function SectionLabel({ n, title }: { n: string; title: string }) {
  return (
    <div className="flex items-center gap-4 font-mono text-[11px] uppercase tracking-[0.22em] text-ink-soft">
      <span className="text-ink">§ {n}</span>
      <span className="h-px w-12 bg-ink" />
      <span>{title}</span>
    </div>
  );
}
