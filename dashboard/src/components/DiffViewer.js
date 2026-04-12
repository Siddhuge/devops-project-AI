export default function DiffViewer({ diff }) {

  if (!diff || diff.length === 0) {
    return <div>No changes</div>;
  }

  return (
    <div>
      {diff.map((d, index) => {

        const lines = d.diff ? d.diff.split("\n") : [];

        return (
          <div key={index} className="mb-6">

            <h3 className="font-bold text-sm mb-2">
              {d.file}
            </h3>

            <pre className="bg-gray-900 text-green-400 p-3 text-xs overflow-auto">
              {lines.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
            </pre>

          </div>
        );
      })}
    </div>
  );
}