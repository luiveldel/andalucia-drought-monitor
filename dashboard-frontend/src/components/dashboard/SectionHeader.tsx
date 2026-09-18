export function SectionHeader(props: { title: string; description?: string }) {
  return (
    <div className="mb-3">
      <h2 className="font-display text-base font-semibold tracking-tight text-ink dark:text-ink-dark">{props.title}</h2>
      {props.description ? (
        <p className="mt-1 text-xs text-muted dark:text-muted-dark">{props.description}</p>
      ) : null}
    </div>
  );
}
