import type { ProviderCapability } from "../lib/types";

type CapabilityMatrixProps = {
  providers: ProviderCapability[];
};

export function CapabilityMatrix({ providers }: CapabilityMatrixProps) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {providers.map((provider) => (
        <article className="glass-panel rounded-[1.6rem] p-5" key={provider.name}>
          <p className="text-xs uppercase tracking-[0.28em] text-clay">
            {provider.name}
          </p>
          <h3 className="mt-2 text-xl font-semibold">{provider.display_name}</h3>
          <p className="mt-3 text-sm text-ink/65">
            Sources: {provider.source_types.join(", ")}
          </p>
          <p className="mt-2 text-sm text-ink/65">
            Formats: {provider.supported_formats.join(", ") || "not advertised"}
          </p>
          <div className="mt-4 space-y-2">
            {provider.limitations.map((limitation) => (
              <p className="rounded-2xl bg-ink/5 px-3 py-2 text-sm" key={limitation}>
                {limitation}
              </p>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

