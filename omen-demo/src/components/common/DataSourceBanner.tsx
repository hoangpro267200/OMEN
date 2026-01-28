import type { DataSourceInfo } from '../../hooks/useDataSource';

interface DataSourceBannerProps {
  source: DataSourceInfo;
}

const STYLES: Record<
  DataSourceInfo['type'],
  { bg: string; border: string; icon: string }
> = {
  live: { bg: 'bg-green-500/10', border: 'border-green-500/30', icon: '●' },
  demo: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', icon: '◐' },
  cached: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', icon: '◔' },
  error: { bg: 'bg-red-500/10', border: 'border-red-500/30', icon: '✕' },
};

export function DataSourceBanner({ source }: DataSourceBannerProps) {
  const s = STYLES[source.type];
  const label =
    source.type === 'demo'
      ? 'DỮ LIỆU DEMO'
      : source.type === 'error'
        ? 'LỖI KẾT NỐI'
        : source.type === 'cached'
          ? 'DỮ LIỆU ĐÃ LƯU'
          : source.isStale
            ? 'DỮ LIỆU CŨ'
            : '';

  if (source.type === 'live' && !source.isStale) return null;

  return (
    <div className={`mx-6 mt-4 px-4 py-3 rounded-lg border ${s.bg} ${s.border}`}>
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-lg">{s.icon}</span>
          <div>
            {label ? <span className="font-medium block">{label}</span> : null}
            <p className="text-sm opacity-90">{source.message}</p>
          </div>
        </div>
        {source.timestamp ? (
          <span className="text-xs opacity-60 shrink-0">
            Cập nhật: {new Date(source.timestamp).toLocaleTimeString('vi-VN')}
          </span>
        ) : null}
      </div>
    </div>
  );
}
