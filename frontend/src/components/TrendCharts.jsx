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
  plugins: {
    legend: { display: false },
    tooltip: { backgroundColor: "#163b45", padding: 11, displayColors: false }
  },
  scales: {
    x: { grid: { display: false }, border: { display: false }, ticks: { color: "#82949b", font: { family: "Poppins", size: 10 } } },
    y: { border: { display: false, dash: [4, 4] }, grid: { color: "#edf1f3" }, ticks: { color: "#82949b", font: { family: "Poppins", size: 10 }, maxTicksLimit: 5 } }
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
          pointRadius: 3,
          tension: 0.38,
          borderWidth: 2.5,
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
          maxBarThickness: 24
        }]
      }}
      options={baseOptions}
    />
  );
}
