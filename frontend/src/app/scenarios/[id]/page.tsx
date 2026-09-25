"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getScenario, createRun, type Scenario, type FaultStep } from "@/lib/api";
import ScenarioCard from "@/components/ScenarioCard";

export default function ScenarioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getScenario(Number(id)).then(setScenario);
  }, [id]);

  const handleLaunch = async () => {
    if (!scenario) return;
    setLaunching(true);
    setError("");
    try {
      const run = await createRun(scenario.id);
      router.push(`/runs/${run.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start run";
      setError(msg);
    } finally {
      setLaunching(false);
    }
  };

  if (!scenario) return <p className="text-gray-500">Loading…</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{scenario.title}</h1>
          <p className="text-sm text-gray-500 mt-0.5">Scenario #{scenario.id}</p>
        </div>
        {scenario.status === "approved" && (
          <button
            onClick={handleLaunch}
            disabled={launching}
            className="px-5 py-2.5 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {launching ? "Launching…" : "▶ Launch Run"}
          </button>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2 mb-4">
          {error}
        </p>
      )}

      {scenario.status !== "approved" && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl px-4 py-3 text-sm text-yellow-700 mb-4">
          This scenario must be <strong>approved</strong> before it can be executed.
        </div>
      )}

      <ScenarioCard
        scenario={scenario}
        onApprove={() => {}}
        onReject={() => {}}
      />
    </div>
  );
}
