import * as echarts from 'echarts';
import { useEffect, useRef } from 'react';

interface Props {
  points: number[];
  color: string;
}

export default function IndexMiniChart({ points, color }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      grid: { left: 0, right: 0, top: 2, bottom: 0 },
      xAxis: { type: 'category', show: false, data: points.map((_, i) => i) },
      yAxis: { type: 'value', show: false },
      series: [
        {
          type: 'line',
          data: points,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1.5, color },
          areaStyle: { color },
        },
      ],
    });
    return () => chart.dispose();
  }, [points, color]);
  return <div ref={ref} style={{ width: '100%', height: 40 }} />;
}
