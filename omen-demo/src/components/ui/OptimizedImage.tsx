import { useState, useEffect } from 'react';
import { cn } from '../../lib/utils';

export interface OptimizedImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  className?: string;
}

/**
 * Progressive image loading with lazy decode and optional dimensions.
 */
export function OptimizedImage({
  src,
  alt,
  width,
  height,
  className,
}: OptimizedImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [currentSrc, setCurrentSrc] = useState<string | undefined>();

  useEffect(() => {
    const img = new Image();
    img.src = src;
    img.onload = () => {
      setCurrentSrc(src);
      setIsLoaded(true);
    };
  }, [src]);

  return (
    <div className={cn('relative overflow-hidden', className)}>
      {!isLoaded && (
        <div
          className="absolute inset-0 animate-pulse bg-[var(--bg-tertiary)]"
          style={{ width, height }}
          aria-hidden
        />
      )}
      {currentSrc && (
        <img
          src={currentSrc}
          alt={alt}
          width={width}
          height={height}
          loading="lazy"
          decoding="async"
          className={cn(
            'transition-opacity duration-300',
            isLoaded ? 'opacity-100' : 'opacity-0'
          )}
        />
      )}
    </div>
  );
}
