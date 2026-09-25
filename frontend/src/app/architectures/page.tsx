"use client";

import { useEffect, useState } from "react";
import { listArchitectures, type Architecture } from "@/lib/api";
import Link from "next/link";

export default function ArchitecturesPage() {
  const [architectures, setArchitectures] = useState<Architecture[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listArchitectures().then(setArchitectures).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading…</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Architectures</h1>
        <Link
          href="/architectures/new"
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
        >
          + New
        </Link>
      </div>

      {architectures.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-400 mb-4">No architectures yet.</p>
          <Link href="/architectures/new" className="text-blue-600 hover:underline text-sm">
            Create your first architecture →
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {architectures.map((arch) => {
            const services = JSON.parse(arch.services_json) as { name: string; type: string }[];
            return (
              <Link
                key={arch.id}
                href={`/architectures/${arch.id}/scenarios`}
                className="block bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-300 transition"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-semibold text-gray-900">{arch.name}</h2>
                    {arch.description && (
                      <p className="text-sm text-gray-500 mt-0.5">{arch.description}</p>
                    )}
                    <div className="flex flex-wrap gap-1 mt-2">
                      {services.map((s) => (
                        <span
                          key={s.name}
                          className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full"
                        >
                          {s.name} ({s.type})
                        </span>
                      ))}
                    </div>
                  </div>
                  <span className="text-xs text-gray-400 shrink-0 ml-4">
                    {new Date(arch.created_at).toLocaleDateString()}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
