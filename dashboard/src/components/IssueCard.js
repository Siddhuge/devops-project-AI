export default function IssueCard({ issue }) {
  return (
    <div className="bg-white p-4 rounded shadow hover:shadow-lg transition">

      {/* Header */}
      <div className="flex justify-between items-center">
        <h3 className="font-bold text-gray-800">{issue.id}</h3>

        <span className={`text-xs px-2 py-1 rounded font-semibold
          ${issue.severity === "CRITICAL" ? "bg-red-500 text-white" :
            issue.severity === "HIGH" ? "bg-orange-500 text-white" :
            issue.severity === "MEDIUM" ? "bg-yellow-400 text-black" :
            "bg-green-500 text-white"}`}>
          {issue.severity}
        </span>
      </div>

      {/* Package */}
      <div className="text-sm mt-2 text-gray-700">
        <b>Package:</b> {issue.package}
      </div>

      {/* Fix */}
      <div className="text-sm text-gray-700">
        <b>Fix:</b> {issue.fix || "Not available"}
      </div>

      {/* Confidence */}
      <div className="text-sm mt-2 text-blue-600 font-semibold">
        Confidence: {issue.confidence}%
      </div>

    </div>
  );
}