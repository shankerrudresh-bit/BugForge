"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  listScenarios,
  generateScenarios,
  updateScenarioStatus,
  type Scenario,
  type FaultStep,
} from "@/lib/api";
import ScenarioCard from "@/components/ScenarioCard";

export default function ScenariosPage() {
  const { id } = useParams<{ id: string }>();
  const archId = Number(id);
  const router = useRouter();

  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  const fetchScenarios = () => {
    setLoading(true);
    listScenarios(archId)
      .then(setScenarios)
      .catch(() => setError("Failed to load scenarios"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchScenarios();
  }, [archId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      await generateScenarios(archId, 3);
      fetchScenarios();
    } catch {
      setError("LLM generation failed. Check backend logs.");
    } finally {
      setGenerating(false);
    }
  };

  const handleStatus = async (scenarioId: number, status: "approved" | "rejected") => {
    await updateScenarioStatus(scenarioId, status);
    setScenarios((prev) =>
      prev.map((s) => (s.id === scenarioId ? { ...s, status } : s))
    );
  };

  if (loading) return <p className="text-gray-500 py-8">Loading scenarios…</p>;

  const draft = scenarios.filter((s) => s.status === "draft");
  const approved = scenarios.filter((s) => s.status === "approved");
  const rejected = scenarios.filter((s) => s.status === "rejected");

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Chaos Scenarios</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Review AI-generated scenarios. Approve to enable execution.
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {generating ? "Generating…" : "↻ Regenerate"}
        </button>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2 mb-4">
          {error}
        </p>
      )}

      {scenarios.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-400 mb-4">No scenarios generated yet.</p>
          <button onClick={handleGenerate} className="text-blue-600 hover:underline text-sm">
            Generate scenarios →
          </button>
        </div>
      )}

      {[
        { label: "Awaiting Review", items: draft, accent: "border-yellow-300" },
        { label: "Approved", items: approved, accent: "border-green-300" },
        { label: "Rejected", items: rejected, accent: "border-gray-200" },
      ].map(
        ({ label, items, accent }) =>
          items.length > 0 && (
            <div key={label} className="mb-8">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                {label} ({items.length})
              </h2>
              <div className="space-y-4">
                {items.map((scenario) => (
                  <ScenarioCard
                    key={scenario.id}
                    scenario={scenario}
                    accentClass={accent}
                    onApprove={() => handleStatus(scenario.id, "approved")}
                    onReject={() => handleStatus(scenario.id, "rejected")}
                    onLaunch={() => router.push(`/scenarios/${scenario.id}`)}
                  />
                ))}
              </div>
            </div>
          )
      )}
    </div>
  );
}
