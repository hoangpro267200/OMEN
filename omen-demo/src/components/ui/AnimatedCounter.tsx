/**
 * Animated Counter
 *
 * Counts up/down to target value with animation.
 * Respects reduced-motion preference.
 */

import { useEffect, useState, useRef } from 'react'
import { motion, useSpring } from 'framer-motion'
import { useReducedMotion } from '../../hooks/useReducedMotion'
import { cn } from '../../lib/utils'

interface AnimatedCounterProps {
  value: number
  duration?: number
  className?: string
  prefix?: string
  suffix?: string
}

/**
 * Spring-based animated counter with prefix/suffix.
 */
export function AnimatedCounter({
  value,
  duration: _duration = 1,
  className = '',
  prefix = '',
  suffix = '',
}: AnimatedCounterProps) {
  const reduced = useReducedMotion()
  const [display, setDisplay] = useState(value)
  const spring = useSpring(value, {
    stiffness: 60,
    damping: 30,
    mass: 0.5,
  })

  useEffect(() => {
    if (reduced) {
      setDisplay(value)
      return
    }
    spring.set(value)
  }, [value, reduced, spring])

  useEffect(() => {
    if (reduced) return
    const unsub = spring.on('change', (v) => setDisplay(Math.round(v)))
    return () => unsub()
  }, [spring, reduced])

  const str = reduced ? String(Math.round(value)) : Math.round(display).toLocaleString()

  return (
    <span className={cn('tabular-nums', className)}>
      {prefix}
      <motion.span
        key={value}
        initial={reduced ? false : { opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.15 }}
      >
        {str}
      </motion.span>
      {suffix}
    </span>
  )
}

/**
 * RequestAnimationFrame-based counter; no spring dependency.
 */
export function SimpleAnimatedCounter({
  value,
  duration = 1000,
  className = '',
}: {
  value: number
  duration?: number
  className?: string
}) {
  const reduced = useReducedMotion()
  const [displayValue, setDisplayValue] = useState(reduced ? value : 0)
  const previousValue = useRef(value)

  useEffect(() => {
    if (reduced) {
      setDisplayValue(value)
      previousValue.current = value
      return
    }
    const startValue = previousValue.current
    const endValue = value
    const startTime = Date.now()

    const animate = () => {
      const now = Date.now()
      const progress = Math.min((now - startTime) / duration, 1)
      const eased = 1 - (1 - progress) ** 3
      const current = Math.round(startValue + (endValue - startValue) * eased)
      setDisplayValue(current)
      if (progress < 1) requestAnimationFrame(animate)
    }
    requestAnimationFrame(animate)
    previousValue.current = value
  }, [value, duration, reduced])

  return (
    <span className={cn('tabular-nums', className)}>
      {(reduced ? value : displayValue).toLocaleString()}
    </span>
  )
}
