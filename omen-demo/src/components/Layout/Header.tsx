import { Shield, Circle } from 'lucide-react';

interface HeaderProps {
  isProcessing: boolean;
  hasSignal: boolean;
}

export function Header({ isProcessing, hasSignal }: HeaderProps) {
  return (
    <header className="border-b border-white/10 bg-black/20 backdrop-blur-xl sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
            <Shield className="w-6 h-6 text-blue-400" />
          </div>
          <span className="text-xl font-bold text-white tracking-tight">
            OMEN
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Circle
            className={`w-2.5 h-2.5 ${
              isProcessing
                ? 'text-amber-400 animate-pulse'
                : hasSignal
                  ? 'text-emerald-400 fill-emerald-400'
                  : 'text-zinc-500'
            }`}
          />
          <span className="text-zinc-400">
            {isProcessing ? 'Processing…' : hasSignal ? 'Signal ready' : 'Demo mode'}
          </span>
        </div>
      </div>
    </header>
  );
}
