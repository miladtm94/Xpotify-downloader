import { CapabilityMatrix } from "../components/CapabilityMatrix";
import type { ProviderCapability } from "../lib/types";

type AboutPageProps = {
  providers: ProviderCapability[];
};

export function AboutPage({ providers }: AboutPageProps) {
  return (
    <section className="space-y-6">
      <div className="glass-panel rounded-[2rem] p-6">
        <p className="text-xs uppercase tracking-[0.35em] text-clay">About and legal</p>
        <h2 className="display-font mt-2 text-4xl font-semibold">A local-first media workbench.</h2>
        <div className="mt-5 max-w-3xl space-y-3 text-ink/70">
          <p>
            Xpotify is a local media manager built on top of the open-source spotDL project.
            It preserves spotDL's Spotify metadata and audio matching workflow while adding
            a modular provider layer and a modern local UI.
          </p>
          <p>
            It does not download audio directly from Spotify. Spotify links are used for
            metadata, and audio matching depends on lawful configured sources.
          </p>
          <p>
            Use this application only for media you own, have permission to download, or can
            lawfully access. DRM bypass, private-content scraping, account-cookie extraction,
            and anti-bot circumvention are intentionally out of scope.
          </p>
        </div>
      </div>
      <CapabilityMatrix providers={providers} />
    </section>
  );
}

