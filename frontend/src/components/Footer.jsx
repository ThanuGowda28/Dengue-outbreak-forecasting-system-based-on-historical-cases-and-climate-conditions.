import { FiActivity, FiGithub } from "react-icons/fi";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="site-footer landing-footer">
      <div className="container">
        <div className="footer-main">
          <div className="footer-brand"><span className="brand-mark"><FiActivity /></span><span><strong>Dengue<span className="brand-accent">Watch</span></strong><small>Climate-aware health insights</small></span></div>
          <div className="footer-column"><strong>Explore</strong><Link to="/">Home</Link><Link to="/about">About the project</Link><Link to="/climate">Climate factors</Link><Link to="/risk-map">Risk map</Link></div>
          <div className="footer-column"><strong>Health information</strong><Link to="/symptoms">Symptoms</Link><Link to="/prevention">Prevention</Link><Link to="/faq">FAQ</Link><Link to="/contact">Contact</Link></div>
          <div className="footer-column"><strong>Project</strong><a href="https://github.com/ThanuGowda28/Dengue-outbreak-forecasting-system-based-on-historical-cases-and-climate-conditions" target="_blank" rel="noreferrer"><FiGithub /> Project repository</a><Link to="/privacy-policy">Privacy notice</Link><Link to="/terms-of-use">Terms of use</Link></div>
        </div>
        <div className="footer-bottom"><span>&copy; {new Date().getFullYear()} DengueWatch · Academic project demonstration</span><span>Not a diagnosis or substitute for professional care.</span></div>
      </div>
    </footer>
  );
}
