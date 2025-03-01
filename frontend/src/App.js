import React, { useState, useEffect } from 'react';
import ApexCharts from 'react-apexcharts';
import './App.css';

// Define unique colors for each chart
const colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A1', '#A133FF', '#33FFA1', '#FFA133'];

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

  // WebSocket connection with reconnection logic
  useEffect(() => {
    let ws;

    const connectWebSocket = () => {
      ws = new WebSocket('ws://localhost:8000/ws');

      ws.onopen = () => {
        console.log('WebSocket connection established');
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Received message:', message);

        if (message.type === 'metrics') {
          const newMetric = message.data;
          setMetricsData((prevData) => ({
            ...prevData,
            bytesSentData: [...prevData.bytesSentData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.bytes_sent }],
            bytesRecvData: [...prevData.bytesRecvData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.bytes_recv }],
            throughputSentData: [...prevData.throughputSentData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.throughput_sent }],
            throughputRecvData: [...prevData.throughputRecvData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.throughput_recv }],
            externalLatencyData: [...prevData.externalLatencyData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.external_ping.avg_latency }],
            externalPacketLossData: [...prevData.externalPacketLossData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.external_ping.packet_loss }],
            localLatencyData: [...prevData.localLatencyData, { x: new Date(newMetric.timestamp).getTime(), y: newMetric.local_ping.avg_latency }],
          }));
        } else if (message.type === 'attack_detection') {
          setAttackDetected(message.data.attack_detected);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket connection closed');
        setTimeout(connectWebSocket, 5000); // Reconnect after 5 seconds
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        ws.close(); // Trigger onclose for reconnection
      };
    };

    connectWebSocket();

    return () => {
      if (ws) ws.close();
    };
  }, []);

  // Define metrics for charts
  const metrics = [
    { name: 'Bytes Sent', data: metricsData.bytesSentData, unit: 'bytes' },
    { name: 'Bytes Received', data: metricsData.bytesRecvData, unit: 'bytes' },
    { name: 'Throughput Sent', data: metricsData.throughputSentData, unit: 'B/s' },
    { name: 'Throughput Received', data: metricsData.throughputRecvData, unit: 'B/s' },
    { name: 'External Latency', data: metricsData.externalLatencyData, unit: 'ms' },
    { name: 'External Packet Loss', data: metricsData.externalPacketLossData, unit: '%' },
    { name: 'Local Latency', data: metricsData.localLatencyData, unit: 'ms' },
  ];

  // Chart configuration with color parameter
  const chartOptions = (title, yAxisLabel, color) => ({
    chart: {
      type: 'line',
      height: 300, // Increased height
      animations: { enabled: true, easing: 'linear', dynamicAnimation: { speed: 1000 } },
      toolbar: { show: true, tools: { zoom: true, pan: true } },
    },
    xaxis: {
      type: 'datetime',
      labels: { style: { fontSize: '12px' } }, // Larger font
    },
    yaxis: {
      title: { text: yAxisLabel },
      labels: {
        style: { fontSize: '12px' }, // Larger font
        formatter: (value) => title === 'External Packet Loss' ? `${(value * 100).toFixed(2)}%` : value,
      },
      ...(title === 'External Packet Loss' ? { min: 0, max: 1 } : {}),
    },
    title: {
      text: title,
      align: 'center',
      style: { fontSize: '16px' }, // Larger title
    },
    stroke: {
      width: 2,
      curve: 'smooth',
      colors: [color], // Unique color per chart
    },
    markers: { size: 0 },
    tooltip: { x: { format: 'HH:mm:ss' } },
  });

  return (
    <div className="app">
      <h1>Network Monitoring Dashboard</h1>
      {attackDetected && <div className="alert">Attack Detected!</div>}
      <div className="chart-grid">
        {metrics.map((metric, index) => (
          <div key={index} className="chart-container">
            <ApexCharts
              options={chartOptions(metric.name, metric.unit, colors[index % colors.length])}
              series={[{ name: metric.name, data: metric.data }]}
              type="line"
              height={300} // Match increased height
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default App;