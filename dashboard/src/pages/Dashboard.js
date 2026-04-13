import { useEffect, useState } from "react";
import axios from "axios";

import Header from "../components/Header";
import Filters from "../components/Filters";
import IssueCard from "../components/IssueCard";
import Stats from "../components/Stats";
import Charts from "../components/Charts";
import HistoryChart from "../components/LineChart";
import DiffViewer from "../components/DiffViewer";

export default function Dashboard() {

  const [issues, setIssues] = useState([]);
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [lastScan, setLastScan] = useState(null);

  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [newRepo, setNewRepo] = useState("");

  const [language, setLanguage] = useState("");

  const [diff, setDiff] = useState([]);
  const [showDiff, setShowDiff] = useState(false);

  const [prStatus, setPrStatus] = useState(null);
  const [lastPRNumber, setLastPRNumber] = useState(null); // 🔥 NEW

  // =========================
  // Load repos
  // =========================
  const loadRepos = async () => {
    try {
      const res = await axios.get("http://localhost:8000/onboarded");
      setRepos(res.data.repos || []);

      if (res.data.repos?.length > 0) {
        setSelectedRepo(res.data.repos[0]);
      }
    } catch {
      console.log("Failed to load repos");
    }
  };

  // =========================
  // Add repo
  // =========================
  const addRepo = async () => {
    if (!newRepo) return;

    await axios.post("http://localhost:8000/onboard", {
      repo: newRepo
    });

    setNewRepo("");
    loadRepos();
  };

  // =========================
  // Scan
  // =========================
  const runScan = async () => {
    if (!selectedRepo) {
      alert("Select repo first");
      return;
    }

    try {
      setLoading(true);

      const res = await axios.post("http://localhost:8000/scan", {
        repo: selectedRepo
      });

      setIssues(res.data.issues || []);
      setLanguage(res.data.language || "unknown");

      const hist = await axios.get(
        `http://localhost:8000/history?repo=${selectedRepo}`
      );

      setHistory(hist.data.history || []);
      setLastScan(new Date().toLocaleString());

    } catch {
      alert("Scan failed");
    } finally {
      setLoading(false);
    }
  };

  // =========================
  // Preview Fix
  // =========================
  const previewFix = async () => {
    if (!selectedRepo) {
      alert("Select repo first");
      return;
    }

    try {
      const res = await axios.post(
        "http://localhost:8000/preview-fix",
        { repo: selectedRepo }
      );

      if (res.data.message) {
        alert(res.data.message);
        return;
      }

      setDiff(res.data.diffs || []);
      setShowDiff(true);

    } catch {
      alert("Preview failed");
    }
  };

  // =========================
  // 🚀 Create PR (ENHANCED)
  // =========================
  const createPR = async () => {
    if (!selectedRepo) {
      alert("Select repo first");
      return;
    }

    try {
      const res = await axios.post(
        "http://localhost:8000/create-pr",
        { repo: selectedRepo }
      );

      if (res.data.url) {
        alert("PR Created:\n" + res.data.url);

        // 🔥 NEW: store PR number for tracking
        if (res.data.number) {
          setLastPRNumber(res.data.number);
        }

      } else {
        alert(res.data.message || "PR Created");
      }

      setShowDiff(false);

    } catch (err) {
      console.error(err);

      const msg =
        err?.response?.data?.error ||
        err?.message ||
        "PR creation failed";

      alert(msg);
    }
  };

  // =========================
  // 🔁 PR Status (ENHANCED)
  // =========================
  const checkStatus = async () => {
    try {
      const res = await axios.get("http://localhost:8000/pr-status");
      setPrStatus(res.data);

      // 🔥 AUTO RESCAN WHEN MERGED
      if (res.data.merged) {
        console.log("[AUTO] PR merged → triggering re-scan");
        await runScan();
      }

    } catch {
      console.log("Failed to fetch PR status");
    }
  };

  // =========================
  // 🔥 AUTO POLLING (NEW)
  // =========================
  useEffect(() => {
    if (!lastPRNumber) return;

    const interval = setInterval(() => {
      checkStatus();
    }, 5000); // every 5 sec

    return () => clearInterval(interval);
  }, [lastPRNumber]);

  useEffect(() => {
    loadRepos();
  }, []);

  // =========================
  // Filter
  // =========================
  const filtered = issues
    .filter(i => filter === "ALL" || i.severity === filter)
    .filter(i =>
      i.id.toLowerCase().includes(search.toLowerCase()) ||
      i.package?.toLowerCase().includes(search.toLowerCase())
    );

  return (
    <div className="bg-gray-100 min-h-screen">

      <Header />

      <div className="p-6">

        <div className="flex justify-between mb-3">

          <div className="flex space-x-2 items-center">

            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="p-2 border rounded"
            >
              <option value="">Select Repo</option>
              {repos.map((repo, i) => (
                <option key={i} value={repo}>{repo}</option>
              ))}
            </select>

            <input
              placeholder="username/repo"
              value={newRepo}
              onChange={(e) => setNewRepo(e.target.value)}
              className="p-2 border rounded"
            />

            <button onClick={addRepo} className="bg-indigo-600 text-white px-3 py-2 rounded">
              ➕ Add
            </button>

            <input
              placeholder="Search..."
              onChange={(e) => setSearch(e.target.value)}
              className="p-2 border rounded"
            />

          </div>

          <div className="space-x-2">

            <button onClick={runScan} className="bg-blue-600 text-white px-4 py-2 rounded">
              🔄 Scan
            </button>

            <button onClick={previewFix} className="bg-purple-600 text-white px-4 py-2 rounded">
              🔍 Preview
            </button>

            <button onClick={checkStatus} className="bg-gray-700 text-white px-4 py-2 rounded">
              📊 PR Status
            </button>

          </div>

        </div>

        <div className="text-sm mb-2">
          Language: <b>{language}</b>
        </div>

        <div className="text-sm text-gray-600 mb-2">
          Last Scan: {lastScan || "Never"}
        </div>

        {prStatus && (
          <div className="mb-4 p-2 bg-white rounded shadow">
            PR: {prStatus.state} | Merged: {prStatus.merged?.toString()}
          </div>
        )}

        <Stats issues={issues} />
        <Charts issues={issues} />
        <HistoryChart data={history} />

        <Filters setFilter={setFilter} />

        {loading && <div className="text-center mt-5">Scanning...</div>}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          {!loading && filtered.map((issue, i) => (
            <IssueCard key={i} issue={issue} />
          ))}
        </div>

      </div>

      {showDiff && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center">

          <div className="bg-white w-3/4 h-3/4 p-4 rounded overflow-auto">

            <h2 className="font-bold mb-2">🔍 PR Preview</h2>

            <DiffViewer diff={diff} />

            <div className="mt-4 flex justify-end space-x-2">
              <button onClick={() => setShowDiff(false)}>Close</button>
              <button onClick={createPR}>🚀 Create PR</button>
            </div>

          </div>

        </div>
      )}

    </div>
  );
}