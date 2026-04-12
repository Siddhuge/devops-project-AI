export default function Filters({ setFilter }) {
  const levels = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

  return (
    <div className="mb-4">
      {levels.map(level => (
        <button
          key={level}
          onClick={() => setFilter(level)}
          className="mr-2 px-3 py-1 bg-blue-500 text-white rounded"
        >
          {level}
        </button>
      ))}
    </div>
  );
}