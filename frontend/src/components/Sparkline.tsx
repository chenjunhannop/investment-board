import * as echarts from 'echarts';
import { useEffect, useRef } from 'react';

interface SparklineProps {
  data: number[];
}

export default function Sparkline({ data }: SparklineProps) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: { left: 0, right: 0, top: 2, bottom: 0 },
      xAxis: { type: 'category', show: false, data: data.map((_, i) => i) },
      yAxis: { type: 'value', show: false },
      series: [
        {
          type: 'line',
          data,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1.5, color: '#4f9cf9' },
        },
      ],
    });
    return () => chart.dispose();
  }, [data]);
  return <div ref={ref} style={{ width: 120, height: 40 }} />;
}
