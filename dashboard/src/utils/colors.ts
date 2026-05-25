import type { Opportunity } from '../types/api'

export function scoreCircleColor(score: number): string {
  if (score >= 85) return '#3fb950'
  if (score >= 75) return '#d29922'
  if (score >= 65) return '#388bfd'
  return '#8b949e'
}

export function tierColor(tier: number): string {
  if (tier === 1) return '#3fb950'
  if (tier === 2) return '#d29922'
  return '#8b949e'
}

export function gradeColor(grade: string | null, score: number): string {
  if (grade === 'EXCELLENT' || score >= 85) return '#3fb950'
  if (grade === 'GOOD' || score >= 75) return '#d29922'
  if (grade === 'WATCH' || score >= 65) return '#388bfd'
  return '#8b949e'
}

export function gradeLabel(grade: string | null, score: number): string {
  if (grade) return grade
  if (score >= 85) return 'EXCELLENT'
  if (score >= 75) return 'GOOD'
  if (score >= 65) return 'WATCH'
  return 'LOW'
}

export function directionColor(direction: string): string {
  return direction === 'LONG' ? '#3fb950' : '#f85149'
}

export function scoreToGradeBucket(score: number): 'excellent' | 'good' | 'watch' | 'below' {
  if (score >= 85) return 'excellent'
  if (score >= 75) return 'good'
  if (score >= 65) return 'watch'
  return 'below'
}

export function filterOpportunities(
  items: Opportunity[],
  gradeFilter: string,
  strategyFilter: string,
): Opportunity[] {
  return items.filter((item) => {
    const grade = gradeLabel(item.grade, item.total_score)
    if (gradeFilter === 'excellent' && grade !== 'EXCELLENT') return false
    if (gradeFilter === 'good' && grade !== 'GOOD') return false
    if (gradeFilter === 'watch' && grade !== 'WATCH') return false
    if (strategyFilter !== 'all' && item.strategy !== strategyFilter) return false
    return true
  })
}
