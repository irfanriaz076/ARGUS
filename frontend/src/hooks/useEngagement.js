import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { engagementsApi, targetsApi, scansApi, findingsApi } from '../api/client'

export function useEngagements() {
  return useQuery({ queryKey: ['engagements'], queryFn: engagementsApi.list })
}

export function useEngagement(id) {
  return useQuery({
    queryKey: ['engagement', id],
    queryFn: () => engagementsApi.get(id),
    enabled: !!id,
  })
}

export function useTargets(engId) {
  return useQuery({
    queryKey: ['targets', engId],
    queryFn: () => targetsApi.list(engId),
    enabled: !!engId,
  })
}

export function useScans(engId) {
  return useQuery({
    queryKey: ['scans', engId],
    queryFn: () => scansApi.list(engId),
    enabled: !!engId,
    refetchInterval: 5000,
  })
}

export function useFindings(engId, filters) {
  return useQuery({
    queryKey: ['findings', engId, filters],
    queryFn: () => findingsApi.list(engId, filters),
    enabled: !!engId,
  })
}

export function useFindingsCount() {
  return useQuery({
    queryKey: ['findings-count'],
    queryFn: findingsApi.count,
    refetchInterval: 30000,
  })
}

export function useAllFindings(filters) {
  return useQuery({
    queryKey: ['all-findings', filters],
    queryFn: () => findingsApi.listAll(filters),
  })
}

export function useCreateEngagement() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: engagementsApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['engagements'] }),
  })
}

export function useStartEngagement() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: engagementsApi.start,
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ['engagement', id] })
      qc.invalidateQueries({ queryKey: ['engagements'] })
    },
  })
}

export function useRerunEngagement() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: engagementsApi.rerun,
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ['engagement', id] })
      qc.invalidateQueries({ queryKey: ['engagements'] })
      qc.invalidateQueries({ queryKey: ['scans', id] })
      qc.invalidateQueries({ queryKey: ['findings', id] })
      qc.invalidateQueries({ queryKey: ['kill-chain', id] })
      qc.invalidateQueries({ queryKey: ['findings-count'] })
    },
  })
}

export function useDeleteEngagement() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: engagementsApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['engagements'] }),
  })
}

export function useAddTarget(engId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => targetsApi.add(engId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['targets', engId] }),
  })
}

export function useKillChain(engId, isRunning) {
  return useQuery({
    queryKey: ['kill-chain', engId],
    queryFn: () => engagementsApi.killChain(engId),
    enabled: !!engId,
    refetchInterval: isRunning ? 4000 : false,
  })
}

export function useDeleteTarget(engId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (targetId) => targetsApi.delete(engId, targetId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['targets', engId] }),
  })
}
