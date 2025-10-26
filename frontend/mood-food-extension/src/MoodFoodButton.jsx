import React, { useMemo, useState } from "react";

/**
 * Drop-in React component to trigger the backend pipeline and show results.
 * - Expects your FastAPI server at API_BASE (default http://127.0.0.1:8000).
 * - Calls POST /api/run with username, token, and optional pickup/dropoff fields.
 * - Displays commits, recommendation, and a clickable DoorDash order_url if present.
 *
 * Tailwind classes are used for quick styling; remove/replace if not using Tailwind.
 */

const API_BASE = import.meta?.env?.VITE_API_BASE || "http://127.0.0.1:8000";

export default function MoodFoodButton() {
  const [username, setUsername] = useState("");
  const [token, setToken] = useState("");

  // Optional delivery fields (backend has sane defaults if you leave these blank)
  const [dropoffAddress, setDropoffAddress] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [pickupAddress, setPickupAddress] = useState("");
  const [pickupBusinessName, setPickupBusinessName] = useState("");
  const [pickupPhoneNumber, setPickupPhoneNumber] = useState("");

  const [loading, setLoading] = useState(false);
  const [commits, setCommits] = useState([]);
  const [result, setResult] = useState(null); // { commits, recommendation, order_response, order_url, note }
  const [error, setError] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  const canRun = useMemo(() => username.trim() && token.trim(), [username, token]);

  const handleRun = async () => {
    if (!canRun) {
      setError("Please enter both username and token.");
      return;
    }
    setError("");
    setLoading(true);
    setCommits([]);
    setResult(null);

    try {
      const resp = await fetch(`${API_BASE}/api/run`, {
        method: "POST",
        headers: {
          accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username.trim(),
          token: token.trim(),
          // Optional fields; backend fills defaults if omitted/empty
          dropoff_address: dropoffAddress || undefined,
          contact_name: contactName || undefined,
          contact_phone: contactPhone || undefined,
          pickup_address: pickupAddress || undefined,
          pickup_business_name: pickupBusinessName || undefined,
          pickup_phone_number: pickupPhoneNumber || undefined,
          poll: true,
        }),
      });

      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(`Server error ${resp.status}: ${text || resp.statusText}`);
      }

      const data = await resp.json();

      if (!data || !Array.isArray(data.commits)) {
        throw new Error("Unexpected API shape: expected { commits: string[] }");
      }

      const msgs = data.commits.map((m) =>
        typeof m === "string" && m.trim() ? m.trim() : "(no commit message)"
      );

      setCommits(msgs);
      setResult(data);
    } catch (e) {
      console.error(e);
      setError(e?.message || "Failed to run pipeline. Check backend/CORS/token.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-4 space-y-4">
      <h2 className="text-2xl font-semibold">Mood → Food 🍣🍕 (GitHub → DoorDash)</h2>

      {/* Credentials */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium mb-1">GitHub Username</label>
          <input
            className="w-full border rounded-md px-3 py-2"
            placeholder="octocat"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        </div>
        <div>
            <label className="block text-sm font-medium mb-1">GitHub Token (classic or fine-grained)</label>
            <input
              type="password"
              className="w-full border rounded-md px-3 py-2"
              placeholder="ghp_********************************"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              autoComplete="current-password"
            />
        </div>
      </div>

      {/* Advanced (optional) */}
      <div className="border rounded-lg">
        <button
          type="button"
          className="w-full text-left px-4 py-3 hover:bg-gray-50 flex items-center justify-between"
          onClick={() => setShowAdvanced((v) => !v)}
        >
          <span className="font-medium">Advanced: Pickup/Dropoff (optional)</span>
          <span className="text-sm text-gray-500">{showAdvanced ? "Hide" : "Show"}</span>
        </button>
        {showAdvanced && (
          <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3 border-t">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1">Dropoff Address</label>
              <input
                className="w-full border rounded-md px-3 py-2"
                placeholder="200 Sample Dropoff Ave, HomeTown, HT 54321"
                value={dropoffAddress}
                onChange={(e) => setDropoffAddress(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Contact Name</label>
              <input
                className="w-full border rounded-md px-3 py-2"
                placeholder="Your Name"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Contact Phone</label>
              <input
                className="w-full border rounded-md px-3 py-2"
                placeholder="+1 555 000 2222"
                value={contactPhone}
                onChange={(e) => setContactPhone(e.target.value)}
              />
            </div>

            <div className="md:col-span-2 border-t my-2" />

            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1">Pickup Address</label>
              <input
                className="w-full border rounded-md px-3 py-2"
                placeholder="100 Sample Pickup St, FoodCity, FC 12345"
                value={pickupAddress}
                onChange={(e) => setPickupAddress(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Pickup Business Name</label>
              <input
                className="w-full border rounded-md px-3 py-2"
                placeholder="Sample Restaurant"
                value={pickupBusinessName}
                onChange={(e) => setPickupBusinessName(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Pickup Phone</label>
              <input
                className="w-full border rounded-md px-3 py-2"
                placeholder="+1 555 000 1111"
                value={pickupPhoneNumber}
                onChange={(e) => setPickupPhoneNumber(e.target.value)}
              />
            </div>
          </div>
        )}
      </div>

      {/* Run button */}
      <div className="flex items-center gap-2">
        <button
          onClick={handleRun}
          disabled={!canRun || loading}
          className={`px-4 py-2 rounded-md text-white ${
            canRun && !loading ? "bg-blue-600 hover:bg-blue-700" : "bg-gray-400"
          }`}
        >
          {loading ? "Running…" : "Analyze commits & order food"}
        </button>
        <span className="text-xs text-gray-500">POST {API_BASE}/api/run</span>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 rounded-md bg-red-50 text-red-700 border border-red-200">
          {error}
        </div>
      )}

      {/* Commits */}
      {commits.length > 0 && (
        <div className="p-4 border rounded-lg">
          <div className="font-semibold mb-2">Latest commit messages</div>
          <ul className="list-disc pl-5 space-y-1 text-sm">
            {commits.map((c, i) => (
              <li key={i} className="break-words">{c}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendation + DoorDash link */}
      {result?.recommendation && (
        <div className="p-4 border rounded-lg bg-gray-50">
          <div className="text-sm text-gray-800 space-y-1">
            <div>
              <span className="font-semibold">Mood:</span>{" "}
              {String(result.recommendation.mood ?? "—")}
            </div>
            <div>
              <span className="font-semibold">Recommended food:</span>{" "}
              {String(result.recommendation.food ?? "—")}
            </div>
            {result.note && (
              <div className="text-xs text-gray-500 mt-1">{result.note}</div>
            )}
            {result.order_url && (
              <div className="mt-2">
                <a
                  href={result.order_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-red-600 underline font-medium"
                >
                  Track / view your DoorDash order
                </a>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Raw JSON (debug) */}
      {result && (
        <div className="border rounded-lg">
          <button
            type="button"
            className="w-full text-left px-4 py-3 hover:bg-gray-50 flex items-center justify-between"
            onClick={() => setShowRaw((v) => !v)}
          >
            <span className="font-medium">Debug: Raw API response</span>
            <span className="text-sm text-gray-500">{showRaw ? "Hide" : "Show"}</span>
          </button>
          {showRaw && (
            <pre className="p-4 text-xs overflow-auto bg-black text-green-200 rounded-b-lg">
{JSON.stringify(result, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
