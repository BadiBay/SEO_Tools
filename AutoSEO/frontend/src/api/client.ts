/**
 * AutoSEO API Client — типизированные вызовы к бэкенду.
 */

const API_BASE = '/api';

export interface Project {
  id: string;
  name: string;
  domain: string;
  region: string | null;
  client_priorities: Record<string, unknown> | null;
  client_logo_url: string | null;
  favicon_url: string | null;
  site_description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PipelineRun {
  id: string;
  project_id: string;
  module_type: string;
  status: string;
  config: Record<string, unknown> | null;
  progress: {
    current_step: number;
    total_steps: number;
    percent: number;
    message: string;
  } | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface Competitor {
  id: string;
  domain: string;
  is_direct_competitor: boolean | null;
  ai_classification_reason: string | null;
  traffic_keys_so: number | null;
  visibility_keys_so: number | null;
  top10_count: number | null;
  visibility_trend: string | null;
  visibility_color: string | null;
  has_ppc: boolean | null;
  ppc_budget_estimate: number | null;
  ppc_budget_trend: string | null;
  has_brand_queries: boolean | null;
  has_commercial_queries: boolean | null;
  domain_age_years: number | null;
  semrush_domain_rating: number | null;
  semrush_backlinks_count: number | null;
  semrush_link_trend: string | null;
  top_pages: Record<string, unknown> | null;
  utp_analysis: Record<string, unknown> | null;
  semantic_structure: Record<string, unknown> | null;
}

// === Module 2: Free Links ===

export interface DonorPlatform {
  id: string;
  name: string;
  url: string;
  platform_type: string;
  requires_logo: boolean;
  requires_captcha: boolean;
  status: string;
  last_checked_at: string | null;
  created_at: string;
}

export interface FreeLink {
  id: string;
  project_id: string;
  donor_id: string;
  target_url: string;
  placed_url: string | null;
  anchor_text: string | null;
  email_alias: string | null;
  promo_text: string | null;
  status: string;
  last_http_code: number | null;
  is_indexed: boolean;
  placed_at: string | null;
  last_checked_at: string | null;
  indexed_at: string | null;
  created_at: string;
  donor?: DonorPlatform;
}

// === Module 3: Paid Links ===

export interface PaidLink {
  id: string;
  project_id: string;
  cluster_id: string | null;
  donor_domain: string;
  donor_page_url: string | null;
  article_title: string | null;
  article_html: string | null;
  status: string;
  price: number | null;
  is_indexed_google: boolean;
  is_indexed_yandex: boolean;
  published_at: string | null;
  created_at: string;
  meta_title?: string | null;
  meta_description?: string | null;
  webmaster_instructions?: string | null;
  tone_check_passed?: boolean | null;
  structure_check_passed?: boolean | null;
}

export interface CompetitorReport {
  id: string;
  run_id: string;
  project_id: string;
  created_at: string;
  competitors: Competitor[];
  marker_queries_count: number;
  direct_competitors_count: number;
  total_competitors: number;
}

// === Generic ===
export interface ListResponse<T> {
  items: T[];
  total: number;
}

// === Module 4: Alt Tags ===

export interface ImageAlt {
  id: string;
  batch_id: string;
  image_src: string;
  page_url: string | null;
  page_h1: string | null;
  page_title: string | null;
  original_alt: string | null;
  original_alt_is_junk: boolean;
  generated_alt: string | null;
  generated_title: string | null;
  image_type: string;
  status: string;
  error_message: string | null;
}

export interface AltTagBatch {
  id: string;
  run_id: string;
  project_id: string;
  site_description: string | null;
  total_images: number;
  processed_images: number;
  skipped_svg: number;
  created_at: string;
  images: ImageAlt[] | null;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || resp.statusText);
  }
  if (resp.status === 204) {
    return undefined as unknown as T;
  }
  return resp.json();
}

// Projects
export const api = {
  getProjects: () => request<{ items: Project[]; total: number }>('/projects'),

  createProject: (data: { name: string; domain: string; region?: string }) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),

  getProject: (id: string) => request<Project>(`/projects/${id}`),

  getProjectRuns: (id: string) => request<PipelineRun[]>(`/projects/${id}/pipeline-runs`),

  updateProjectFreeLinksInfo: (id: string, data: { target_url?: string; promo_text?: string; account_data?: string }) =>
    request<Project>(`/projects/${id}/free-links-info`, { method: 'PUT', body: JSON.stringify(data) }),

  // Competitors
  savePriorities: (data: {
    project_id: string;
    directions: string[];
    top_services?: string[];
    notes?: string;
  }) => request<{ status: string }>('/competitors/priorities', {
    method: 'POST', body: JSON.stringify(data),
  }),

  startAnalysis: (data: { project_id: string; config?: Record<string, unknown> }) =>
    request<PipelineRun>('/competitors/analyze', {
      method: 'POST', body: JSON.stringify(data),
    }),

  getReport: (reportId: string) =>
    request<CompetitorReport>(`/competitors/reports/${reportId}`),

  getReportByRun: (runId: string) =>
    request<CompetitorReport>(`/competitors/reports/by-run/${runId}`),

  // Runs
  getRunStatus: (runId: string) => request<PipelineRun & { steps: unknown[] }>(`/runs/${runId}`),

  // Paid Links
  createPaidLink: (data: { project_id: string; main_keyword: string; donor_domain: string }) =>
    request<PaidLink>('/paid-links', {
      method: 'POST', body: JSON.stringify(data),
    }),
  getPaidLinks: (projectId: string) =>
    request<{ items: PaidLink[]; total: number }>(`/paid-links/project/${projectId}`),
  getPaidLinkDetails: (linkId: string) =>
    request<PaidLink & { meta_title?: string; meta_description?: string; webmaster_instructions?: string; tone_check_passed?: boolean; structure_check_passed?: boolean }>(`/paid-links/${linkId}`),
  generatePaidLinkArticle: (linkId: string) =>
    request<{ task_id: string; message: string }>(`/paid-links/${linkId}/generate`, {
      method: 'POST',
    }),
  getPaidDonors: (projectId?: string) => 
    request<ListResponse<DonorPlatform>>(`/paid-links/donors/list${projectId ? `?project_id=${projectId}` : ''}`),
  importPaidLinks: (projectId: string, data: { links: { domain: string; placed_url?: string; price?: number; miralinks_order_id?: string }[] }) =>
    request<{ message: string; created_donors: number; created_links: number }>(`/paid-links/project/${projectId}/import`, { method: 'POST', body: JSON.stringify(data) }),

  // Free Links
  getDonors: (projectId?: string) => request<ListResponse<DonorPlatform>>(`/free-links/donors${projectId ? `?project_id=${projectId}` : ''}`),
  createDonor: (data: Partial<DonorPlatform>) => request<DonorPlatform>('/free-links/donors', { method: 'POST', body: JSON.stringify(data) }),
  getFreeLinks: (projectId: string) => request<ListResponse<FreeLink>>(`/free-links/project/${projectId}`),
  createFreeLink: (data: any) => request<FreeLink>('/free-links', { method: 'POST', body: JSON.stringify(data) }),
  importFreeLinks: (projectId: string, data: { donors: { name: string; url: string; platform_type?: string; placed_url?: string }[] }) =>
    request<{ message: string; created_donors: number; created_links: number }>(`/free-links/project/${projectId}/import`, { method: 'POST', body: JSON.stringify(data) }),
  deleteFreeLink: (linkId: string) => request<void>(`/free-links/${linkId}`, { method: 'DELETE' }),
  generateFreeLinkAssets: (linkId: string) =>
    request<{ message: string }>(`/free-links/${linkId}/generate`, { method: 'POST' }),
  verifyFreeLink: (linkId: string, data: { placed_url: string }) =>
    request<{ message: string }>(`/free-links/${linkId}/verify`, { method: 'POST', body: JSON.stringify(data) }),

  // Alt Tags
  importAltTags: (projectId: string, data: { images: Partial<ImageAlt>[] }) =>
    request<AltTagBatch>(`/alt-tags/project/${projectId}/import`, { method: 'POST', body: JSON.stringify(data) }),
  getAltBatches: (projectId: string) => request<{ items: AltTagBatch[]; total: number }>(`/alt-tags/project/${projectId}/batches`),
  getAltBatch: (batchId: string) => request<AltTagBatch>(`/alt-tags/batch/${batchId}`),

  // Notifications
  getNotifications: (params?: { project_id?: string; unread_only?: boolean }) => {
    const qs = new URLSearchParams()
    if (params?.project_id) qs.append('project_id', params.project_id)
    if (params?.unread_only) qs.append('unread_only', 'true')
    return request<any[]>(`/notifications?${qs.toString()}`)
  },
  markNotificationRead: (id: string) => request<{ status: string }>(`/notifications/${id}/read`, { method: 'PUT' }),

  // Settings
  getSettings: () => request<Record<string, any>>('/settings'),
  updateSettings: (settings: { key: string; value: any }[]) => request<{ status: string }>('/settings', { method: 'PUT', body: JSON.stringify({ settings }) }),

  // Health
  health: () => request<{ status: string }>('/health'),
};
