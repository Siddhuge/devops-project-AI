export default function Stats({ issues }) {

  const count = (sev) => issues.filter(i => i.severity === sev).length;

  const Box = ({ label, value, color }) => (
    <div className={`p-4 rounded shadow text-white ${color}`}>
      <div className="text-sm">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
      <Box label="CRITICAL" value={count("CRITICAL")} color="bg-red-500" />
      <Box label="HIGH" value={count("HIGH")} color="bg-orange-400" />
      <Box label="MEDIUM" value={count("MEDIUM")} color="bg-yellow-400 text-black" />
      <Box label="LOW" value={count("LOW")} color="bg-green-500" />
    </div>
  );
}