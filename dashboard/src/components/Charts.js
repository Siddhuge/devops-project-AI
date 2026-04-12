import { PieChart, Pie, Cell, Tooltip } from "recharts";

export default function Charts({ issues }) {

  const data = [
    { name: "CRITICAL", value: issues.filter(i => i.severity === "CRITICAL").length },
    { name: "HIGH", value: issues.filter(i => i.severity === "HIGH").length },
    { name: "MEDIUM", value: issues.filter(i => i.severity === "MEDIUM").length },
    { name: "LOW", value: issues.filter(i => i.severity === "LOW").length },
  ];

  const COLORS = ["#ef4444", "#fb923c", "#facc15", "#22c55e"];

  return (
    <div className="bg-white p-4 rounded shadow mb-6">
      <h2 className="font-bold mb-2">📊 Severity Distribution</h2>

      <PieChart width={300} height={200}>
        <Pie
          data={data}
          dataKey="value"
          outerRadius={80}
        >
          {data.map((entry, index) => (
            <Cell key={index} fill={COLORS[index]} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </div>
  );
}