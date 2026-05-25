interface CompactStatCardProps {
  label: string
  value: string
  sub?: string
  color?: string
  icon?: React.ReactNode
  compact?: boolean
}

export function CompactStatCard({
  label,
  value,
  sub,
  color,
  icon,
  compact = false,
}: CompactStatCardProps) {
  return (
    <div
      className={`flex flex-col justify-center rounded-lg border border-[#30363d] bg-[#161b22] px-4 ${
        compact ? 'h-[68px] py-2' : 'h-20 py-2'
      }`}
    >
      <div className="mb-0.5 flex items-center justify-between gap-2">
        <span className="truncate text-[10px] font-semibold uppercase tracking-wider text-[#8b949e]">
          {label}
        </span>
        {icon && <span className="shrink-0 opacity-70">{icon}</span>}
      </div>
      <p
        className={`truncate font-mono font-bold ${compact ? 'text-lg' : 'text-xl'}`}
        style={{ color: color ?? '#e6edf3' }}
      >
        {value}
      </p>
      {sub && <p className="mt-0.5 truncate text-[10px] text-[#484f58]">{sub}</p>}
    </div>
  )
}
