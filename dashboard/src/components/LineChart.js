import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";

export default function HistoryChart({ data }) {
  return (
    <div className="bg-white p-4 rounded shadow mb-6">
      <h2 className="font-bold mb-3 text-lg">
        📈 Scan History
      </h2>

      <div className="w-full h-64">
        <ResponsiveContainer>
          <LineChart data={data}>
            <XAxis dataKey="time" />
            <YAxis />
            <Tooltip />
            <Legend />

            <Line type="monotone" dataKey="CRITICAL" stroke="#ef4444" />
            <Line type="monotone" dataKey="HIGH" stroke="#fb923c" />
            <Line type="monotone" dataKey="MEDIUM" stroke="#facc15" />
            <Line type="monotone" dataKey="LOW" stroke="#22c55e" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}