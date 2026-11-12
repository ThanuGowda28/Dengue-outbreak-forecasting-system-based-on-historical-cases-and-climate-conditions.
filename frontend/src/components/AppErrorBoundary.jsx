import { Component } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, RefreshCw, ShieldAlert } from "lucide-react";

export default class AppErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <main className="not-found-page app-error-page">
        <span className="error-illustration" aria-hidden="true"><ShieldAlert size={36} /></span>
        <span className="not-found-code">500</span>
        <h1>We hit an unexpected problem.</h1>
        <p>Your information is safe. Please try again or return to the home page.</p>
        <div className="error-page-actions">
          <button className="btn btn-primary" type="button" onClick={() => window.location.reload()}>
            <RefreshCw size={16} aria-hidden="true" />Try again
          </button>
          <Link className="btn btn-outline-primary" to="/">
            <ArrowLeft size={16} aria-hidden="true" />Home
          </Link>
        </div>
      </main>
    );
  }
}
