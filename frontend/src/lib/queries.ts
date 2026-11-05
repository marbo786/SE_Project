import { useQuery } from '@tanstack/react-query'
import { projectsApi, dashboardApi } from './api'

export function useProjects() {
  return useQuery({ queryKey: ['projects'], queryFn: async ({ signal }) => (await projectsApi.list(signal)).data,
    refetchInterval: query => query.state.data?.some((p: { status: string }) => p.status === 'analyzing') ? 2000 * Math.min(8, 2 ** query.state.fetchFailureCount) : false,
    refetchIntervalInBackground: false })
}

export function useDashboard() {
  return useQuery({ queryKey: ['dashboard'], queryFn: async ({ signal }) => (await dashboardApi.getStats(signal)).data,
    refetchInterval: query => query.state.data?.analyzing_projects ? 2000 * Math.min(8, 2 ** query.state.fetchFailureCount) : false,
    refetchIntervalInBackground: false })
}
