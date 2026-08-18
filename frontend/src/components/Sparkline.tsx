import * as echarts from 'echarts';
import { useEffect, useRef } from 'react';

interface SparklineProps {
  data: number[];
}

export default function Sparkline({ data }: SparklineProps) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const up = data.length >= 2 ? data[data.length - 1] >= data[0] : true;
    const cssVar = up ? '--up' : '--down';
    const color =
      getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim() || '#e5484d';
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
          lineStyle: { width: 1.5, color },
        },
      ],
    });
    return () => chart.dispose();
  }, [data]);
  return <div ref={ref} style={{ width: 120, height: 40 }} />;
}
