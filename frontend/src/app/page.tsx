import Link from "next/link";

export default function HomePage() {
  return (
    <div className="text-center py-20">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">BugForge</h1>
      <p className="text-lg text-gray-500 mb-8 max-w-xl mx-auto">
        AI-driven chaos engineering. Describe your system, get multi-layered fault scenarios, 
        execute them against live containers, and see exactly where your system breaks.
      </p>
      <div className="flex justify-center gap-4">
        <Link
          href="/architectures/new"
          className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
        >
          + New Architecture
        </Link>
        <Link
          href="/architectures"
          className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition"
        >
          View All
        </Link>
      </div>
      <div className="mt-16 grid grid-cols-3 gap-6 text-left max-w-3xl mx-auto">
        {[
          { step: "1", title: "Describe Architecture", desc: "Define your services, dependencies, and SLOs." },
          { step: "2", title: "AI Generates Scenarios", desc: "LLM creates multi-layered compound fault scenarios." },
          { step: "3", title: "Execute & Report", desc: "Inject faults into live containers and get resilience scores." },
        ].map(({ step, title, desc }) => (
          <div key={step} className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-sm mb-3">
              {step}
            </div>
            <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
            <p className="text-sm text-gray-500">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
