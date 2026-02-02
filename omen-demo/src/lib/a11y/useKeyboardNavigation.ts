/**
 * Keyboard Navigation Hook
 *
 * Enables arrow key navigation for lists.
 */

import { useCallback, useState } from 'react'

interface UseKeyboardNavigationOptions {
  itemCount: number
  onSelect?: (index: number) => void
  wrap?: boolean
  orientation?: 'vertical' | 'horizontal'
}

export function useKeyboardNavigation({
  itemCount,
  onSelect,
  wrap = true,
  orientation = 'vertical',
}: UseKeyboardNavigationOptions) {
  const [activeIndex, setActiveIndex] = useState(0)

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      const prevKey = orientation === 'vertical' ? 'ArrowUp' : 'ArrowLeft'
      const nextKey = orientation === 'vertical' ? 'ArrowDown' : 'ArrowRight'

      switch (event.key) {
        case prevKey:
          event.preventDefault()
          setActiveIndex((prev) => {
            if (prev === 0) return wrap ? itemCount - 1 : 0
            return prev - 1
          })
          break
        case nextKey:
          event.preventDefault()
          setActiveIndex((prev) => {
            if (prev === itemCount - 1) return wrap ? 0 : itemCount - 1
            return prev + 1
          })
          break
        case 'Enter':
        case ' ':
          event.preventDefault()
          onSelect?.(activeIndex)
          break
        case 'Home':
          event.preventDefault()
          setActiveIndex(0)
          break
        case 'End':
          event.preventDefault()
          setActiveIndex(Math.max(0, itemCount - 1))
          break
      }
    },
    [itemCount, onSelect, wrap, orientation, activeIndex]
  )

  return {
    activeIndex,
    setActiveIndex,
    handleKeyDown,
  }
}
