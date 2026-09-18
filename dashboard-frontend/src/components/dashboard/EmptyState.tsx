export function EmptyState(props: { title: string; message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-black/20 px-6 py-12 text-center dark:border-white/20">
      <p className="font-display text-lg font-semibold text-ink dark:text-ink-dark">{props.title}</p>
      <p className="mt-2 text-sm text-muted dark:text-muted-dark">{props.message}</p>
    </div>
  );
}
