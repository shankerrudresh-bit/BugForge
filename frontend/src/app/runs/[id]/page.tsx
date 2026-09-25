"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getRun, getRunLogs, type Run, type LogEntry } from "@/lib/api";
import Link from "next/link";

const STATUS_COLOR: Record<string, string> = {
  pending: "bg-gray-100 text-gray-500",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const runId = Number(id);

  const [run, setRun] = useState<Run | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRun = async () => {
    const data = await getRun(runId);
    setRun(data);
    const logData = await getRunLogs(runId);
    setLogs(logData.slice(-100));
    return data;
  };

  useEffect(() => {
    fetchRun().then((data) => {
      if (data.status !== "completed" && data.status !== "failed") {
        intervalRef.current = setInterval(async () => {
          const updated = await fetchRun();
          if (updated.status === "completed" || updated.status === "failed") {
            if (intervalRef.current) clearInterval(intervalRef.current);
          }
        }, 3000);
      }
    });

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [runId]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (!run) return <p className="text-gray-500">Loading run…</p>;

  const isTerminal = run.status === "completed" || run.status === "failed";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Run #{run.id}</h1>
          <p className="text-sm text-gray-500">Scenario #{run.scenario_id}</p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`text-sm px-3 py-1 rounded-full font-medium ${STATUS_COLOR[run.status] || "bg-gray-100 text-gray-500"}`}
          >
            {run.status}
          </span>
          {isTerminal && (
            <Link
              href={`/runs/${run.id}/report`}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
            >
              View Report →
            </Link>
          )}
        </div>
      </div>

      {/* Step timeline */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
        <h2 className="font-semibold text-gray-800 mb-4">Fault Steps</h2>
        <div className="space-y-3">
          {run.steps.map((step) => (
            <div key={step.id} className="flex items-center gap-4">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                  STATUS_COLOR[step.status] || "bg-gray-100 text-gray-500"
                }`}
              >
                {step.step_index + 1}
              </div>
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-mono bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs">
                    {step.fault_type}
                  </span>
                  <span className="text-gray-400 text-xs">→</span>
                  <span className="text-gray-700 text-xs">{step.target_service}</span>
                  <span className="text-gray-400 text-xs">{step.duration_seconds}s</span>
                </div>
                {step.result && (
                  <p className="text-xs mt-0.5 text-gray-500">
                    {step.result.passed ? "✓ Passed" : "✗ Failed"}{" "}
                    {step.result.notes ? `— ${step.result.notes}` : ""}
                  </p>
                )}
              </div>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[step.status]}`}
              >
                {step.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Live log tail */}
      <div className="bg-gray-900 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-300">Container Logs</h2>
          {!isTerminal && (
            <span className="text-xs text-green-400 animate-pulse">● Live</span>
          )}
        </div>
        <div className="h-64 overflow-y-auto font-mono text-xs text-gray-300 space-y-0.5">
          {logs.length === 0 && <p className="text-gray-500">No logs yet…</p>}
          {logs.map((log) => (
            <div key={log.id} className="leading-relaxed">
              <span className="text-gray-500 mr-2">{new Date(log.timestamp).toISOString().slice(11, 23)}</span>
              <span className="text-gray-400 mr-2">[{log.container_name}]</span>
              <span>{log.message}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}
