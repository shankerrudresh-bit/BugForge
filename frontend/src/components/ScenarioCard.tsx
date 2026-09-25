"use client";

import { type Scenario, type FaultStep } from "@/lib/api";

const FAULT_COLORS: Record<string, string> = {
  kill_container: "bg-red-100 text-red-700",
  pause_container: "bg-orange-100 text-orange-700",
  network_partition: "bg-purple-100 text-purple-700",
  cpu_stress: "bg-yellow-100 text-yellow-700",
  memory_stress: "bg-pink-100 text-pink-700",
  inject_latency: "bg-blue-100 text-blue-700",
};

interface Props {
  scenario: Scenario;
  accentClass?: string;
  onApprove: () => void;
  onReject: () => void;
  onLaunch?: () => void;
}

export default function ScenarioCard({ scenario, accentClass = "", onApprove, onReject, onLaunch }: Props) {
  const steps: FaultStep[] = JSON.parse(scenario.steps_json || "[]");

  return (
    <div className={`bg-white border ${accentClass || "border-gray-200"} rounded-xl p-5`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-gray-900">{scenario.title}</h3>
            <StatusBadge status={scenario.status} />
          </div>
          {scenario.description && (
            <p className="text-sm text-gray-500 mb-4">{scenario.description}</p>
          )}

          {/* Fault step timeline */}
          <div className="flex flex-col gap-2">
            {steps.map((step, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="flex flex-col items-center shrink-0">
                  <div className="w-6 h-6 rounded-full bg-gray-100 text-gray-600 text-xs font-bold flex items-center justify-center">
                    {step.step_index + 1}
                  </div>
                  {i < steps.length - 1 && <div className="w-px h-4 bg-gray-200" />}
                </div>
                <div className="flex-1 pb-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        FAULT_COLORS[step.fault_type] || "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {step.fault_type.replace(/_/g, " ")}
                    </span>
                    <span className="text-xs text-gray-500">→</span>
                    <span className="text-xs font-mono bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                      {step.target_service}
                    </span>
                    <span className="text-xs text-gray-400">{step.duration_seconds}s</span>
                  </div>
                  {step.description && (
                    <p className="text-xs text-gray-400 mt-0.5">{step.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-col gap-2 shrink-0">
          {scenario.status !== "approved" && (
            <button
              onClick={onApprove}
              className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Approve
            </button>
          )}
          {scenario.status !== "rejected" && (
            <button
              onClick={onReject}
              className="px-3 py-1.5 text-xs font-medium border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50"
            >
              Reject
            </button>
          )}
          {scenario.status === "approved" && onLaunch && (
            <button
              onClick={onLaunch}
              className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              ▶ Run
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    draft: "bg-yellow-100 text-yellow-700",
    approved: "bg-green-100 text-green-700",
    rejected: "bg-gray-100 text-gray-500",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[status] || "bg-gray-100 text-gray-600"}`}>
      {status}
    </span>
  );
}
