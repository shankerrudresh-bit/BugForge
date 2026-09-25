import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: API_BASE });

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ServiceDefinition {
  name: string;
  type: string;
  dependencies: string[];
  slo_latency_ms?: number;
  slo_availability_pct?: number;
}

export interface Architecture {
  id: number;
  name: string;
  description?: string;
  services_json: string;
  created_at: string;
}

export interface FaultStep {
  step_index: number;
  fault_type: string;
  target_service: string;
  duration_seconds: number;
  parameters: Record<string, unknown>;
  description?: string;
}

export interface Scenario {
  id: number;
  architecture_id: number;
  title: string;
  description?: string;
  steps_json: string;
  status: "draft" | "approved" | "rejected";
  created_at: string;
}

export interface StepResult {
  id: number;
  run_step_id: number;
  passed: boolean;
  health_check_output?: string;
  notes?: string;
}

export interface RunStep {
  id: number;
  run_id: number;
  step_index: number;
  fault_type: string;
  target_service: string;
  parameters_json?: string;
  duration_seconds: number;
  status: "pending" | "running" | "completed" | "failed";
  started_at?: string;
  finished_at?: string;
  result?: StepResult;
}

export interface Run {
  id: number;
  scenario_id: number;
  status: "pending" | "running" | "completed" | "failed";
  started_at?: string;
  finished_at?: string;
  steps: RunStep[];
}

export interface LogEntry {
  id: number;
  run_id: number;
  run_step_id?: number;
  container_name: string;
  timestamp: string;
  message: string;
}

export interface MetricSample {
  id: number;
  run_id: number;
  run_step_id?: number;
  container_name: string;
  cpu_pct: number;
  mem_mb: number;
  sampled_at: string;
}

export interface StepSummary {
  step_index: number;
  fault_type: string;
  target_service: string;
  duration_seconds: number;
  status: string;
  passed: boolean;
  peak_cpu_pct: number;
  peak_mem_mb: number;
  error_log_count: number;
  health_check_output?: string;
}

export interface RunReport {
  run_id: number;
  scenario_id: number;
  scenario_title: string;
  overall_passed: boolean;
  steps: StepSummary[];
  narrative?: string;
}

// ── Architecture API ──────────────────────────────────────────────────────────

export const createArchitecture = (data: {
  name: string;
  description?: string;
  services: ServiceDefinition[];
}) => api.post<Architecture>("/api/architectures", data).then((r) => r.data);

export const listArchitectures = () =>
  api.get<Architecture[]>("/api/architectures").then((r) => r.data);

export const getArchitecture = (id: number) =>
  api.get<Architecture>(`/api/architectures/${id}`).then((r) => r.data);

// ── Scenario API ──────────────────────────────────────────────────────────────

export const generateScenarios = (architecture_id: number, num_scenarios = 3) =>
  api
    .post<Scenario[]>("/api/scenarios/generate", { architecture_id, num_scenarios })
    .then((r) => r.data);

export const listScenarios = (arch_id: number) =>
  api
    .get<Scenario[]>(`/api/architectures/${arch_id}/scenarios`)
    .then((r) => r.data);

export const getScenario = (id: number) =>
  api.get<Scenario>(`/api/scenarios/${id}`).then((r) => r.data);

export const updateScenarioStatus = (id: number, status: string) =>
  api
    .patch<Scenario>(`/api/scenarios/${id}/status`, { status })
    .then((r) => r.data);

// ── Runs API ──────────────────────────────────────────────────────────────────

export const createRun = (scenario_id: number) =>
  api.post<Run>("/api/runs", { scenario_id }).then((r) => r.data);

export const getRun = (id: number) =>
  api.get<Run>(`/api/runs/${id}`).then((r) => r.data);

export const listRuns = (scenario_id?: number) =>
  api
    .get<Run[]>("/api/runs", { params: scenario_id ? { scenario_id } : {} })
    .then((r) => r.data);

export const getRunLogs = (run_id: number, step_id?: number) =>
  api
    .get<LogEntry[]>(`/api/runs/${run_id}/logs`, {
      params: step_id ? { step_id } : {},
    })
    .then((r) => r.data);

export const getRunMetrics = (run_id: number, step_id?: number) =>
  api
    .get<MetricSample[]>(`/api/runs/${run_id}/metrics`, {
      params: step_id ? { step_id } : {},
    })
    .then((r) => r.data);

export const getRunReport = (run_id: number) =>
  api.get<RunReport>(`/api/runs/${run_id}/report`).then((r) => r.data);
