import {
  Chart as ChartJS,
  CategoryScale,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  BarElement,
  Tooltip
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend, Filler);

const baseOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 650, easing: "easeOutQuart" },
  interaction: { intersect: false, mode: "index" },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: "#173943",
      borderColor: "rgba(255,255,255,.12)",
      borderWidth: 1,
      titleFont: { family: "DM Sans", size: 12, weight: "600" },
      bodyFont: { family: "DM Sans", size: 12 },
      padding: 12,
      cornerRadius: 10,
      displayColors: false
    }
  },
  scales: {
    x: {
      grid: { display: false },
      border: { display: false },
      ticks: { color: "#82949b", font: { family: "DM Sans", size: 11 }, maxRotation: 0 }
    },
    y: {
      border: { display: false, dash: [4, 4] },
      grid: { color: "rgba(125,151,158,.14)", drawTicks: false },
      ticks: { color: "#82949b", font: { family: "DM Sans", size: 11 }, maxTicksLimit: 5, padding: 9 }
    }
  }
};

export function DengueLineChart({ labels, data, color = "#009688", fill = false, label = "Trend" }) {
  return (
    <Line
      data={{
        labels,
        datasets: [{
          label,
          data,
          borderColor: color,
          backgroundColor: fill ? `${color}18` : color,
          pointBackgroundColor: "#fff",
          pointBorderColor: color,
          pointBorderWidth: 2,
          pointRadius: labels.length > 14 ? 0 : 3,
          pointHoverRadius: 5,
          tension: 0.34,
          borderWidth: 2.75,
          fill
        }]
      }}
      options={baseOptions}
    />
  );
}

export function DengueBarChart({ labels, data, color = "#009688", label = "Cases" }) {
  return (
    <Bar
      data={{
        labels,
        datasets: [{
          label,
          data,
          backgroundColor: labels.map((_, index) => index === 7 ? color : `${color}35`),
          borderRadius: 5,
          maxBarThickness: 28,
          hoverBackgroundColor: color
        }]
      }}
      options={baseOptions}
    />
  );
}
