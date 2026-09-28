import React from "react";
import { Link } from "react-router-dom";
import { Header } from "../components/Header";
import { ScribeLogo } from "../components/ScribeLogo";

// The three phases the pipeline actually runs through. Laid out as a colophon
// band (mono numerals, vertical rules) rather than three icon circles.
const STAGES = [
  {
    n: "i",
    title: "Ask",
    body: "A company, a market, a question you can’t settle. Write it the way you’d ask a colleague.",
  },
  {
    n: "ii",
    title: "Investigates",
    body: "Scribe plans the search, opens sources in parallel, and cross-references what it turns up.",
  },
  {
    n: "iii",
    title: "Writes it up",
    body: "A structured dossier with its reasoning intact — ready to read, share, or print.",
  },
];

// Deliberately asymmetric: these are not interchangeable features, so they are
// not presented as equal-weight cards in a grid.
const SPEC: { label: string; title: string; body: string; wide?: boolean }[] = [
  {
    label: "Under the hood",
    title: "Three agents, not one long prompt",
    body: "Planning, retrieval and synthesis run as separate stages. A thin answer can’t slip through as a thick one, because the stage that would have produced it never gets to.",
    wide: true,
  },
  {
    label: "While it runs",
    title: "You can see the phases tick over",
    body: "No spinner staring back at you. Close the tab if you like — it lands in your library when it’s done.",
  },
  {
    label: "Afterwards",
    title: "Everything is kept",
    body: "Past reports stay searchable and one click away, with the original query attached.",
  },
  {
    label: "On paper",
    title: "It prints properly",
    body: "Long-form typography and a real print stylesheet, because a report is something you might actually print.",
  },
];

export const LandingPage: React.FC = () => {
  return (
    <div className="flex min-h-screen flex-col bg-background text-on-background antialiased">
      <Header />

      <main className="flex-grow">
        {/* ---------------------------------------------------------- Hero
            Left-aligned with the product itself in the right column. The
            default AI hero is centred copy over a glow — this shows the
            actual artefact instead of decorating around it. */}
        <section className="relative overflow-hidden border-b border-outline-variant">
          <div
            aria-hidden
            className="bg-grid pointer-events-none absolute inset-0"
          />

          <div className="relative mx-auto grid w-full max-w-container-max grid-cols-1 items-center gap-14 px-margin-mobile py-16 md:px-margin-desktop md:py-24 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.92fr)] lg:gap-16">
            <div className="reveal">
              <p className="mb-7 flex items-center gap-3 font-label-sm text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
                <span className="h-px w-8 bg-accent" />
                Research, written up
              </p>

              <h1 className="text-display-lg-mobile text-on-surface md:text-display-lg">
                Give it a subject. Get back a
                <span className="relative ml-2 inline-block italic text-accent">
                  report
                  <svg
                    aria-hidden
                    viewBox="0 0 200 12"
                    preserveAspectRatio="none"
                    className="absolute -bottom-1 left-0 h-2.5 w-full text-accent/45"
                  >
                    <path
                      d="M2 8c46-5 100-6 196-3"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="4"
                      strokeLinecap="round"
                    />
                  </svg>
                </span>
                .
              </h1>

              <p className="mt-8 max-w-[46ch] text-body-md text-on-surface-variant md:text-body-lg">
                Scribe takes a topic apart, works the sources methodically, and
                hands back a properly cited dossier — so you can stay on the
                thinking that actually needs you.
              </p>

              <div className="mt-10 flex w-full flex-col items-stretch gap-3 sm:w-auto sm:flex-row sm:items-center">
                <Link
                  to="/signup"
                  className="btn btn-primary btn-sheen px-7 py-3.5 text-[15px]"
                >
                  Start researching
                  <span className="material-symbols-outlined text-[18px]">
                    arrow_forward
                  </span>
                </Link>
                <Link
                  to="/login"
                  className="btn btn-outline px-7 py-3.5 text-[15px]"
                >
                  I already have an account
                </Link>
              </div>

              <p className="mt-6 font-body-sm text-body-sm text-outline">
                Free in beta · No card required
              </p>
            </div>

            {/* Specimen: a slice of a real report, with a live status line. */}
            <div className="reveal-late lg:justify-self-end">
              <Specimen />
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------ Process */}
        <section className="border-b border-outline-variant bg-surface-container-lowest">
          <div className="mx-auto w-full max-w-container-max px-margin-mobile py-16 md:px-margin-desktop md:py-20">
            <div className="grid grid-cols-1 divide-y divide-outline-variant border-y border-outline-variant md:grid-cols-3 md:divide-x md:divide-y-0">
              {STAGES.map((s) => (
                <div key={s.n} className="px-0 py-8 md:px-8 md:py-10 first:md:pl-0 last:md:pr-0">
                  <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
                    {s.n}
                  </span>
                  <h2 className="mt-3 font-headline-md text-headline-md text-on-surface">
                    {s.title}
                  </h2>
                  <p className="mt-3 max-w-[38ch] text-body-sm text-body-sm leading-relaxed text-on-surface-variant">
                    {s.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* -------------------------------------------------- Specification
            A spec sheet, not a card grid. Rows are unequal on purpose. */}
        <section className="mx-auto w-full max-w-container-max px-margin-mobile py-20 md:px-margin-desktop md:py-28">
          <div className="grid grid-cols-1 gap-x-16 gap-y-12 lg:grid-cols-12">
            <div className="lg:col-span-4">
              <p className="mb-4 font-label-sm text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">
                Details
              </p>
              <h2 className="max-w-[16ch] text-display-lg-mobile text-on-surface md:text-[2.25rem] md:leading-[2.5rem]">
                Once the research lands, the reading starts.
              </h2>
              <p className="mt-6 max-w-[40ch] text-body-md text-body-md text-on-surface-variant">
                Most of the work happens before you see anything. This is the
                part you actually touch.
              </p>
            </div>

            <div className="lg:col-span-8">
              <dl className="flex flex-col">
                {SPEC.map((row) => (
                  <div
                    key={row.title}
                    className={`grid grid-cols-1 gap-2 border-t border-outline-variant py-7 sm:grid-cols-[9rem_minmax(0,1fr)] sm:gap-8 ${
                      row.wide ? "sm:grid-cols-[9rem_minmax(0,1.35fr)]" : ""
                    }`}
                  >
                    <dt className="font-label-sm text-[11px] font-semibold uppercase tracking-[0.14em] text-outline">
                      {row.label}
                    </dt>
                    <dd>
                      <h3 className="font-headline-sm text-headline-sm text-on-surface">
                        {row.title}
                      </h3>
                      <p className="mt-2 max-w-[54ch] text-body-sm text-body-sm leading-relaxed text-on-surface-variant">
                        {row.body}
                      </p>
                    </dd>
                  </div>
                ))}
                <div className="border-t border-outline-variant" />
              </dl>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------ CTA */}
        <section className="border-t border-outline-variant bg-surface-container-lowest">
          <div className="mx-auto w-full max-w-reading-max px-margin-mobile py-20 text-center md:py-28">
            <ScribeLogo glyphOnly className="mx-auto mb-8 h-7 text-accent" alt="" />
            <h2 className="text-display-lg-mobile text-on-surface md:text-display-lg">
              Stop tab-hopping between
              <br className="hidden sm:block" /> twelve open tabs.
            </h2>
            <p className="mx-auto mt-6 max-w-xl text-body-lg text-on-surface-variant">
              Give Scribe the question. Get back something worth reading.
            </p>
            <Link
              to="/signup"
              className="btn btn-primary btn-sheen mt-10 px-8 py-4 text-[15px]"
            >
              Create your free account
              <span className="material-symbols-outlined text-[18px]">
                arrow_forward
              </span>
            </Link>
          </div>
        </section>
      </main>

      <footer
        data-print-hide
        className="border-t border-outline-variant bg-background"
      >
        <div className="mx-auto flex w-full max-w-container-max flex-col items-center justify-between gap-4 px-margin-mobile py-8 sm:flex-row md:px-margin-desktop">
          <ScribeLogo className="h-5 text-[1.15rem] text-on-surface-variant" />
          <p className="font-body-sm text-body-sm text-outline">
            © {new Date().getFullYear()} Scribe — research, written up.
          </p>
        </div>
      </footer>
    </div>
  );
};

// A decorative slice of a finished report. Shows the reading experience
// rather than describing it.
const Specimen: React.FC = () => (
  <div className="relative w-full max-w-[30rem]">
    <div className="rounded-md border border-outline-variant bg-surface">
      <div className="flex items-center justify-between gap-3 border-b border-outline-variant px-5 py-3">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-outline">
          Report · Complete
        </span>
        <span className="inline-flex items-center gap-1.5 font-label-sm text-[11px] text-secondary">
          <span className="h-1.5 w-1.5 rounded-full bg-secondary" />
          4 min read
        </span>
      </div>

      <div className="px-5 py-6">
        <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-outline">
          Energy · Supply chain
        </p>
        <h3 className="mt-2.5 font-serif text-[1.4rem] font-semibold leading-[1.2] tracking-[-0.015em] text-on-surface">
          Sodium-ion batteries: a post-lithium primer
        </h3>

        <div className="font-serif text-[0.94rem] leading-[1.75] text-on-surface">
          <p className="drop-cap">
            Grid-scale storage is shifting. Lithium-ion still dominates, but
            sodium-ion has crossed the threshold where it is economically
            rational for short-duration grid applications.
          </p>
          <p className="mt-4">
            The strategic question is not whether sodium-ion wins on cost — it
            clearly does at four-hour duration — but whether incumbent
            manufacturers can defend margin by moving upmarket faster than
            sodium attackers can scale.
          </p>
        </div>
      </div>
    </div>

    {/* Hanging caption, set off the card's left edge. Kept in normal flow so
        it can never collide with the specimen at any viewport width. */}
    <p className="mt-6 max-w-[30ch] border-l-2 border-accent pl-4 font-body-sm text-body-sm italic leading-relaxed text-on-surface-variant lg:ml-8">
      Every report keeps its original query, so you can always see what it was
      actually asked.
    </p>
  </div>
);
