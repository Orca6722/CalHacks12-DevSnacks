import React, { useState } from 'react';

export default function MoodFoodButton() {
  const [username, setUsername] = useState('');
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [commits, setCommits] = useState([]); // Array<string>

  const fetchCommits = async () => {
    if (!username || !token) {
      setError('Please enter both username and token.');
      return;
    }
    setError('');
    setLoading(true);
    setCommits([]);

    try {
      const resp = await fetch('http://127.0.0.1:8000/api/run', {
        method: 'POST',
        headers: {
          accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, token }),
      });

      if (!resp.ok) throw new Error(`Server error: ${resp.status}`);
      const data = await resp.json();

      if (!data || !Array.isArray(data.commits)) {
        throw new Error('Unexpected API shape: expected { commits: string[] }');
      }

      // data.commits is List[str]
      const msgs = data.commits.map((m) =>
        typeof m === 'string' && m.trim() ? m.trim() : '(no commit message)'
      );
      setCommits(msgs);
    } catch (e) {
      console.error(e);
      setError(e.message || 'Failed to fetch commits. Check backend/CORS/token.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[500px] bg-white p-4">
      <div className="text-center p-6 bg-white rounded-2xl shadow-xl w-full max-w-sm">
        <h1 className="text-3xl font-bold mb-1">
          <span className="text-gray-900">mood</span>
          <span className="text-red-600"> food</span>
        </h1>
        <p className="text-xs text-gray-400 mb-5 tracking-widest">
          AI • CODE • DELIVERY
        </p>

        <input
          type="text"
          placeholder="GitHub Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full mb-3 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
        />
        <input
          type="password"
          placeholder="GitHub Token (repo scope)"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          className="w-full mb-4 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
        />

        <button
          onClick={fetchCommits}
          disabled={loading}
          className={`w-full py-3 text-lg font-bold rounded-xl transition-all duration-300
            ${loading ? 'bg-gray-400' : 'bg-red-600 hover:bg-red-700 hover:scale-105'}
            text-white shadow-lg`}
        >
          {loading ? 'Fetching commits…' : 'Fetch my commits'}
        </button>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-400 text-red-700 rounded-lg text-left">
            {error}
          </div>
        )}

        {commits.length > 0 && (
          <div className="mt-5 text-left">
            <div className="flex items-baseline justify-between mb-2">
              <h2 className="font-semibold text-gray-800">Recent commits</h2>
              <span className="text-xs text-gray-500">{commits.length}</span>
            </div>
            <ol className="max-h-64 overflow-auto border border-gray-200 rounded-lg divide-y list-decimal list-inside">
              {commits.map((msg, idx) => (
                <li key={idx} className="p-3">
                  <div className="text-sm text-gray-900 whitespace-pre-wrap break-words">
                    {msg}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}

        {!loading && !error && commits.length === 0 && (
          <p className="mt-4 text-sm text-gray-500">
            Enter your GitHub creds and click <span className="font-medium">Fetch my commits</span>.
          </p>
        )}
      </div>
    </div>
  );
}
