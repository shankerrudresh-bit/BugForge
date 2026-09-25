"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createArchitecture, generateScenarios, type ServiceDefinition } from "@/lib/api";

const SERVICE_TYPES = ["api", "database", "cache", "worker", "queue", "frontend", "gateway"];

const emptyService = (): ServiceDefinition => ({
  name: "",
  type: "api",
  dependencies: [],
  slo_latency_ms: undefined,
  slo_availability_pct: undefined,
});

export default function NewArchitecturePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [services, setServices] = useState<ServiceDefinition[]>([emptyService()]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const updateService = (idx: number, patch: Partial<ServiceDefinition>) => {
    setServices((prev) => prev.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
  };

  const addService = () => setServices((prev) => [...prev, emptyService()]);

  const removeService = (idx: number) =>
    setServices((prev) => prev.filter((_, i) => i !== idx));

  const handleDepsChange = (idx: number, value: string) => {
    const deps = value
      .split(",")
      .map((d) => d.trim())
      .filter(Boolean);
    updateService(idx, { dependencies: deps });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return setError("Architecture name is required.");
    const invalidServices = services.filter((s) => !s.name.trim());
    if (invalidServices.length > 0) return setError("All services must have a name.");

    setLoading(true);
    setError("");
    try {
      const arch = await createArchitecture({ name, description, services });
      // Immediately kick off scenario generation
      await generateScenarios(arch.id, 3);
      router.push(`/architectures/${arch.id}/scenarios`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Failed: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-1">New Architecture</h1>
      <p className="text-sm text-gray-500 mb-6">
        Describe your system. BugForge will generate chaos scenarios using AI.
      </p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Architecture Name <span className="text-red-500">*</span>
            </label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. E-commerce Platform"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
              placeholder="Brief description of the system"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900">Services</h2>
            <button
              type="button"
              onClick={addService}
              className="text-sm text-blue-600 hover:underline"
            >
              + Add Service
            </button>
          </div>

          <div className="space-y-4">
            {services.map((svc, idx) => (
              <div
                key={idx}
                className="bg-white border border-gray-200 rounded-xl p-5 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                    Service {idx + 1}
                  </span>
                  {services.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeService(idx)}
                      className="text-xs text-red-500 hover:underline"
                    >
                      Remove
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g. api-gateway"
                      value={svc.name}
                      onChange={(e) => updateService(idx, { name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
                    <select
                      className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      value={svc.type}
                      onChange={(e) => updateService(idx, { type: e.target.value })}
                    >
                      {SERVICE_TYPES.map((t) => (
                        <option key={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Dependencies (comma-separated)
                    </label>
                    <input
                      className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g. postgres, redis"
                      value={svc.dependencies.join(", ")}
                      onChange={(e) => handleDepsChange(idx, e.target.value)}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        SLO Latency (ms)
                      </label>
                      <input
                        type="number"
                        className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="200"
                        value={svc.slo_latency_ms ?? ""}
                        onChange={(e) =>
                          updateService(idx, {
                            slo_latency_ms: e.target.value ? Number(e.target.value) : undefined,
                          })
                        }
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        SLO Availability (%)
                      </label>
                      <input
                        type="number"
                        className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="99.9"
                        step="0.1"
                        value={svc.slo_availability_pct ?? ""}
                        onChange={(e) =>
                          updateService(idx, {
                            slo_availability_pct: e.target.value ? Number(e.target.value) : undefined,
                          })
                        }
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:opacity-50 transition"
        >
          {loading ? "Generating scenarios with AI…" : "Create Architecture & Generate Scenarios →"}
        </button>
      </form>
    </div>
  );
}
