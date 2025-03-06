import React, { useState, useEffect, useRef } from 'react';
import ApexCharts from 'react-apexcharts';
import './App.css';

// Define unique colors for charts
const colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A1', '#A133FF', '#33FFA1', '#FFA133'];

// Define bins for categorizing data in pie charts
const metricBins = {
  'Bytes Sent': [100, 500],         // <100, 100-500, >500 bytes
  'Bytes Received': [100, 500],     // <100, 100-500, >500 bytes
  'Throughput Sent': [100, 500],    // <100, 100-500, >500 B/s
  'Throughput Received': [100, 500],// <100, 100-500, >500 B/s
  'External Latency': [50, 100],    // <50, 50-100, >100 ms
  'Local Latency': [50, 100],       // <50, 50-100, >100 ms
  // External Packet Loss is handled separately (0% vs >0%)
};

const App = () => {
  // State for metrics data
  const [metricsData, setMetricsData] = useState({
    bytesSentData: [],
    bytesRecvData: [],
    throughputSentData: [],
    throughputRecvData: [],
    externalLatencyData: [],
    externalPacketLossData: [],
    localLatencyData: [],
  });

  // State for attack detection
  const [attackDetected, setAttackDetected] = useState(false);

  // State for connection status
  const [connectionStatus, setConnectionStatus] = useState('Connecting...');

  // State for active tab
  const [activeTab, setActiveTab] = useState('line');

  // Ref for WebSocket
  const wsRef = useRef(null);

  // Ref for retry count
  const retryCountRef = useRef(0);

  // WebSocket connection function
  const connectWebSocket = () => {
    const ws = new WebSocket('ws://localhost:8000/ws'); // Adjust URL as needed
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connection established');
      setConnectionStatus('Connected');
      retryCountRef.current = 0;
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'metrics') {
        const newMetric = message.data;
        const maxPoints = 100; // Limit to last 100 points
        setMetricsData((prevData) => ({
          bytesSentData: [...prevData.bytesSentData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.bytes_sent }].slice(-maxPoints),
          bytesRecvData: [...prevData.bytesRecvData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.bytes_recv }].slice(-maxPoints),
          throughputSentData: [...prevData.throughputSentData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.throughput_sent }].slice(-maxPoints),
          throughputRecvData: [...prevData.throughputRecvData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.throughput_recv }].slice(-maxPoints),
          externalLatencyData: [...prevData.externalLatencyData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.external_ping.avg_latency }].slice(-maxPoints),
          externalPacketLossData: [...prevData.externalPacketLossData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.external_ping.packet_loss }].slice(-maxPoints),
          localLatencyData: [...prevData.localLatencyData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.local_ping.avg_latency }].slice(-maxPoints),
        }));
      } else if (message.type === 'attack_detection') {
        setAttackDetected(message.data.attack_detected);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed');
      setConnectionStatus('Disconnected');
      const retryDelay = Math.min(1000 * (2 ** retryCountRef.current), 30000);
      setTimeout(() => {
        retryCountRef.current += 1;
        connectWebSocket();
      }, retryDelay);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('Error');
    };
  };

  // Initialize WebSocket on mount
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, []);

  // Define metrics array
  const metrics = [
    { name: 'Bytes Sent', data: metricsData.bytesSentData, unit: 'bytes' },
    { name: 'Bytes Received', data: metricsData.bytesRecvData, unit: 'bytes' },
    { name: 'Throughput Sent', data: metricsData.throughputSentData, unit: 'B/s' },
    { name: 'Throughput Received', data: metricsData.throughputRecvData, unit: 'B/s' },
    { name: 'External Latency', data: metricsData.externalLatencyData, unit: 'ms' },
    { name: 'External Packet Loss', data: metricsData.externalPacketLossData, unit: '%' },
    { name: 'Local Latency', data: metricsData.localLatencyData, unit: 'ms' },
  ];

  // Aggregate data for bar charts
  const aggregateData = (data, intervalMinutes = 5) => {
    if (data.length === 0) return [];
    const intervalMs = intervalMinutes * 60 * 1000;
    const aggregated = {};
    data.forEach((point) => {
      const intervalStart = Math.floor(point.x / intervalMs) * intervalMs;
      if (!aggregated[intervalStart]) {
        aggregated[intervalStart] = { sum: 0, count: 0 };
      }
      aggregated[intervalStart].sum += point.y;
      aggregated[intervalStart].count += 1;
    });
    return Object.entries(aggregated).map(([time, { sum, count }]) => ({
      x: Number(time),
      y: sum / count,
    }));
  };

  // Get pie chart data
  const getPieChartData = (metricName, data) => {
    if (data.length === 0) return { series: [], labels: [] };
    if (metricName === 'External Packet Loss') {
      const noLoss = data.filter(d => d.y === 0).length;
      const loss = data.length - noLoss;
      return {
        series: [noLoss / data.length * 100, loss / data.length * 100],
        labels: ['No Loss', 'Loss'],
      };
    } else {
      const bins = metricBins[metricName];
      if (!bins || bins.length !== 2) return { series: [], labels: [] };
      const low = data.filter(d => d.y < bins[0]).length;
      const medium = data.filter(d => d.y >= bins[0] && d.y < bins[1]).length;
      const high = data.filter(d => d.y >= bins[1]).length;
      const total = data.length;
      return {
        series: [low / total * 100, medium / total * 100, high / total * 100],
        labels: [`Low (<${bins[0]})`, `Medium (${bins[0]}-${bins[1]})`, `High (>${bins[1]})`],
      };
    }
  };

  // Chart options
  const lineChartOptions = (title, yAxisLabel, color) => ({
    chart: { type: 'line', height: 300, animations: { enabled: true, easing: 'linear' } },
    xaxis: { type: 'datetime', labels: { style: { fontSize: '14px' } } },
    yaxis: {
      title: { text: yAxisLabel },
      labels: {
        style: { fontSize: '14px' },
        formatter: (value) => (title === 'External Packet Loss' ? `${(value * 100).toFixed(2)}%` : value.toFixed(2)),
      },
      ...(title === 'External Packet Loss' ? { min: 0, max: 1 } : {}),
    },
    title: { text: title, align: 'center', style: { fontSize: '18px', fontWeight: 'bold' } },
    stroke: { width: 2, curve: 'smooth' },
    colors: [color],
    tooltip: { x: { format: 'HH:mm:ss' } },
  });

  const barChartOptions = (title, yAxisLabel) => ({
    chart: { type: 'bar', height: 300 },
    xaxis: { type: 'datetime', labels: { style: { fontSize: '14px' } } },
    yaxis: {
      title: { text: yAxisLabel },
      labels: { style: { fontSize: '14px' } },
    },
    title: { text: title, align: 'center', style: { fontSize: '18px', fontWeight: 'bold' } },
    plotOptions: { bar: { horizontal: false } },
    colors: [colors[0]],
    tooltip: { x: { format: 'HH:mm:ss' } },
  });

  const pieChartOptions = (title, labels) => ({
    chart: { type: 'pie', height: 300 },
    labels,
    title: { text: title, align: 'center', style: { fontSize: '18px', fontWeight: 'bold' } },
    colors: colors.slice(0, labels.length),
  });

  return (
    <div className="app">
      <h1>Network Monitoring Dashboard</h1>
      <div className={`connection-status ${connectionStatus.toLowerCase()}`}>
        Connection Status: {connectionStatus}
      </div>
      {attackDetected && <div className="alert">Attack Detected!</div>}
      <div className="tabs">
        <button className={activeTab === 'line' ? 'active' : ''} onClick={() => setActiveTab('line')}>
          Line Charts
        </button>
        <button className={activeTab === 'bar' ? 'active' : ''} onClick={() => setActiveTab('bar')}>
          Bar Graphs
        </button>
        <button className={activeTab === 'pie' ? 'active' : ''} onClick={() => setActiveTab('pie')}>
          Pie Charts
        </button>
      </div>
      <div className="chart-grid">
        {activeTab === 'line' &&
          metrics.map((metric, index) => (
            <div key={index} className="chart-container">
              <ApexCharts
                options={lineChartOptions(metric.name, metric.unit, colors[index % colors.length])}
                series={[{ name: metric.name, data: metric.data }]}
                type="line"
                height={300}
              />
            </div>
          ))}
        {activeTab === 'bar' &&
          metrics.map((metric, index) => {
            const aggregatedData = aggregateData(metric.data);
            return (
              <div key={index} className="chart-container">
                <ApexCharts
                  options={barChartOptions(`Average ${metric.name} per 5-min`, metric.unit)}
                  series={[{ name: metric.name, data: aggregatedData }]}
                  type="bar"
                  height={300}
                />
              </div>
            );
          })}
        {activeTab === 'pie' &&
          metrics.map((metric, index) => {
            const { series, labels } = getPieChartData(metric.name, metric.data);
            if (series.length === 0) return null;
            return (
              <div key={index} className="chart-container">
                <ApexCharts
                  options={pieChartOptions(`${metric.name} Distribution`, labels)}
                  series={series}
                  type="pie"
                  height={300}
                />
              </div>
            );
          })}
      </div>
    </div>
  );
};

export default App;