"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getRunReport, getRunMetrics, type RunReport, type MetricSample } from "@/lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

export default function RunReportPage() {
  const { id } = useParams<{ id: string }>();
  const runId = Number(id);

  const [report, setReport] = useState<RunReport | null>(null);
  const [metrics, setMetrics] = useState<MetricSample[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getRunReport(runId), getRunMetrics(runId)])
      .then(([rep, met]) => {
        setReport(rep);
        setMetrics(met);
      })
      .catch((err) => setError(err?.response?.data?.detail || "Failed to load report"))
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) return <p className="text-gray-500">Loading report…</p>;
  if (error)
    return (
      <p className="text-red-600 bg-red-50 border border-red-200 rounded-xl px-4 py-3">{error}</p>
    );
  if (!report) return null;

  // Group metrics by step
  const metricsByStep: Record<number, MetricSample[]> = {};
  metrics.forEach((m) => {
    const key = m.run_step_id ?? -1;
    if (!metricsByStep[key]) metricsByStep[key] = [];
    metricsByStep[key].push(m);
  });

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Run Report #{report.run_id}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{report.scenario_title}</p>
        </div>
        <div
          className={`px-4 py-2 rounded-xl font-semibold text-sm ${
            report.overall_passed
              ? "bg-green-100 text-green-700"
              : "bg-red-100 text-red-700"
          }`}
        >
          {report.overall_passed ? "✓ Resilient" : "✗ Failures Detected"}
        </div>
      </div>

      {/* LLM Narrative */}
      {report.narrative && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-6">
          <h2 className="font-semibold text-blue-800 mb-2">AI Resilience Assessment</h2>
          <p className="text-sm text-blue-700 whitespace-pre-line">{report.narrative}</p>
        </div>
      )}

      {/* Per-step summaries */}
      <div className="space-y-4 mb-8">
        {report.steps.map((step) => {
          const stepMetrics = metricsByStep[step.step_index] || [];
          const chartData = stepMetrics.map((m, i) => ({
            t: i,
            cpu: Number(m.cpu_pct.toFixed(1)),
            mem: Number(m.mem_mb.toFixed(1)),
          }));

          return (
            <div
              key={step.step_index}
              className={`bg-white border rounded-xl p-5 ${
                step.passed ? "border-green-200" : "border-red-200"
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-900">
                      Step {step.step_index + 1}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        step.passed ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                      }`}
                    >
                      {step.passed ? "Passed" : "Failed"}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-1">
                    <span className="text-xs font-mono bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                      {step.fault_type}
                    </span>
                    <span className="text-xs text-gray-500">→ {step.target_service}</span>
                    <span className="text-xs text-gray-400">{step.duration_seconds}s</span>
                  </div>
                </div>
                <div className="text-right text-xs text-gray-500 space-y-0.5">
                  <div>Peak CPU: <span className="font-semibold text-gray-700">{step.peak_cpu_pct}%</span></div>
                  <div>Peak Mem: <span className="font-semibold text-gray-700">{step.peak_mem_mb} MB</span></div>
                  <div>Error Logs: <span className={`font-semibold ${step.error_log_count > 0 ? "text-red-600" : "text-gray-700"}`}>{step.error_log_count}</span></div>
                </div>
              </div>

              {step.health_check_output && (
                <pre className="text-xs bg-gray-50 rounded-lg p-3 text-gray-600 mb-3 overflow-x-auto">
                  {step.health_check_output}
                </pre>
              )}

              {chartData.length > 1 && (
                <div className="mt-3">
                  <p className="text-xs text-gray-400 mb-1">CPU % + Memory MB over step duration</p>
                  <ResponsiveContainer width="100%" height={140}>
                    <LineChart data={chartData}>
                      <XAxis dataKey="t" hide />
                      <YAxis yAxisId="left" width={30} tick={{ fontSize: 10 }} />
                      <YAxis yAxisId="right" orientation="right" width={35} tick={{ fontSize: 10 }} />
                      <Tooltip
                        contentStyle={{ fontSize: 11 }}
                        formatter={(value: number, name: string) =>
                          [name === "cpu" ? `${value}%` : `${value} MB`, name === "cpu" ? "CPU" : "Memory"]
                        }
                      />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="cpu"
                        stroke="#3b82f6"
                        dot={false}
                        strokeWidth={1.5}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="mem"
                        stroke="#f59e0b"
                        dot={false}
                        strokeWidth={1.5}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
