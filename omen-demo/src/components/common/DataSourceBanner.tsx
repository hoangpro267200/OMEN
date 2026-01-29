import type { DataSourceInfo } from '../../hooks/useDataSource';

interface DataSourceBannerProps {
  source: DataSourceInfo;
  onRetry?: () => void;
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

export function DataSourceBanner({ source, onRetry }: DataSourceBannerProps) {
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
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-lg shrink-0">{s.icon}</span>
          <div className="min-w-0">
            {label ? <span className="font-medium block">{label}</span> : null}
            <p className="text-sm opacity-90">{source.message}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {source.timestamp ? (
            <span className="text-xs opacity-60">
              Cập nhật: {new Date(source.timestamp).toLocaleTimeString('vi-VN')}
            </span>
          ) : null}
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="px-3 py-1.5 rounded text-sm font-medium bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 hover:bg-cyan-500/30"
            >
              Thử lại
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
