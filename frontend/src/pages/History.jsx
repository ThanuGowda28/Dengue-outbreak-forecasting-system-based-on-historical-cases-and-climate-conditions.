import { useEffect, useState } from "react";
import { FiActivity, FiTarget, FiTrash2 } from "react-icons/fi";
import { Link } from "react-router-dom";
import { EmptyState, Pagination, RiskIndicator } from "../components/DashboardComponents.jsx";
import AlertMessage from "../components/AlertMessage.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import {
  deletePredictionHistory,
  getPredictionHistory,
} from "../services/predictionService.js";

export default function History() {
  const [history, setHistory] = useState({
    items: [],
    pagination: { page: 1, total_pages: 0, total_items: 0 },
  });
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [risk, setRisk] = useState("");
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function handleDelete(item) {
    if (!window.confirm(`Delete the ${item.risk_level} risk prediction for ${item.state}?`)) {
      return;
    }
    setDeletingId(item.id);
    setError("");
    setNotice("");
    try {
      await deletePredictionHistory(item.id);
      setNotice("Prediction history record deleted.");
      if (history.items.length === 1 && page > 1) {
        setPage(page - 1);
      } else {
        setHistory((current) => ({
          ...current,
          items: current.items.filter((record) => record.id !== item.id),
          pagination: {
            ...current.pagination,
            total_items: Math.max(0, current.pagination.total_items - 1),
          },
        }));
      }
    } catch (deleteError) {
      setError(
        deleteError.response?.data?.message ||
          "Prediction history record could not be deleted.",
      );
    } finally {
      setDeletingId(null);
    }
  }

  useEffect(() => {
    let active = true;
    setLoading(true);
    const timer = window.setTimeout(() => {
      getPredictionHistory({
        page,
        per_page: 10,
        search: search.trim(),
        risk: risk || undefined,
      })
        .then((data) => {
          if (active) {
            setHistory(data);
            setError("");
          }
        })
        .catch((historyError) => {
          if (active) {
            setError(
              historyError.response?.data?.message ||
                "Prediction history could not be loaded.",
            );
          }
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, search ? 300 : 0);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [page, risk, search]);

  return (
    <div className="dashboard-page">
      <div className="page-intro">
        <span className="page-overline">YOUR ACTIVITY</span>
        <h2>Prediction history</h2>
        <p>Saved results from the annual climate-based ensemble classifier.</p>
      </div>
      {error && <AlertMessage message={error} />}
      {notice && (
        <AlertMessage
          message={notice}
          variant="success"
          onDismiss={() => setNotice("")}
        />
      )}
      <section className="surface-card">
        <div className="surface-heading">
          <div>
            <h2>Saved predictions</h2>
            <p>{history.pagination.total_items} records</p>
          </div>
          <Link to="/prediction" className="btn btn-outline-primary btn-sm">
            <FiTarget className="me-2" />
            Prepare climate inputs
          </Link>
        </div>
        <div className="row g-2 mb-3">
          <div className="col-md-8">
            <label className="visually-hidden" htmlFor="history-search">
              Search prediction history
            </label>
            <input
              id="history-search"
              className="form-control"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Search state / UT"
            />
          </div>
          <div className="col-md-4">
            <label className="visually-hidden" htmlFor="history-risk">
              Filter by risk
            </label>
            <select
              id="history-risk"
              className="form-select"
              value={risk}
              onChange={(event) => {
                setRisk(event.target.value);
                setPage(1);
              }}
            >
              <option value="">All risk levels</option>
              <option value="Low">Low</option>
              <option value="Moderate">Moderate</option>
              <option value="High">High</option>
            </select>
          </div>
        </div>
        {loading ? (
          <LoadingSpinner label="Loading prediction history..." />
        ) : history.items.length ? (
          <div className="table-responsive">
            <table className="table align-middle">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>State / UT</th>
                  <th>Risk</th>
                  <th>Top-class probability</th>
                  <th><span className="visually-hidden">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {history.items.map((item) => (
                  <tr key={item.id}>
                    <td>{new Date(item.prediction_time).toLocaleString()}</td>
                    <td>{item.state}</td>
                    <td>
                      <RiskIndicator level={item.risk_level} />
                    </td>
                    <td>{Number(item.confidence).toFixed(2)}%</td>
                    <td className="text-end">
                      <button
                        type="button"
                        className="btn btn-outline-danger btn-sm"
                        aria-label={`Delete prediction for ${item.state} (${item.risk_level} risk)`}
                        disabled={deletingId !== null}
                        onClick={() => handleDelete(item)}
                      >
                        <FiTrash2 className="me-1" />
                        {deletingId === item.id ? "Deleting..." : "Delete"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={FiActivity}
            title="No prediction history found"
            description="Saved model classifications matching these filters will appear here."
            action={
              <Link
                to="/prediction"
                className="btn btn-outline-primary btn-sm mt-3"
              >
                <FiTarget className="me-2" />
                Create a prediction
              </Link>
            }
          />
        )}
        {!loading && history.items.length > 0 && (
          <Pagination
            page={history.pagination.page || 1}
            pageCount={history.pagination.total_pages || 0}
            onChange={setPage}
          />
        )}
      </section>
    </div>
  );
}
