import { motion } from "framer-motion";
import { Activity, CloudSun, HeartPulse, ShieldCheck } from "lucide-react";

export default function AuthStory({ variant = "login" }) {
  const isRegister = variant === "register";

  return (
    <motion.aside
      className="auth-story"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
    >
      <span className="auth-story-kicker"><ShieldCheck size={15} /> COMMUNITY HEALTH FORECASTING</span>
      <h2>{isRegister ? "Better prepared starts with better insight." : "Health insights, centered on your community."}</h2>
      <p>Explore local climate conditions and dengue outlooks designed to support informed awareness.</p>
      <div className="auth-story-visual" aria-hidden="true">
        <span className="auth-story-orbit auth-story-orbit-one" />
        <span className="auth-story-orbit auth-story-orbit-two" />
        <span className="auth-story-center"><HeartPulse size={35} strokeWidth={1.6} /></span>
        <span className="auth-story-weather"><CloudSun size={21} /><small>Climate</small></span>
        <span className="auth-story-community"><Activity size={20} /><small>Community</small></span>
      </div>
      <div className="auth-story-footnote"><ShieldCheck size={16} />Private account access for your health workspace</div>
    </motion.aside>
  );
}
