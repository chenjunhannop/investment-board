import * as echarts from 'echarts';
import { useEffect, useRef } from 'react';
import type { SectorRow } from '../api/client';

export default function FundFlowChart({ data }: { data: SectorRow[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const names = data.map((d) => d.name);
    const flows = data.map((d) => d.fund_flow / 1e8); // 亿
    chart.setOption({
      grid: { left: 60, right: 30, top: 8, bottom: 24 },
      tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${v.toFixed(2)} 亿` },
      xAxis: { type: 'value', show: false },
      yAxis: { type: 'category', data: names, axisLabel: { color: '#7c8b9c', fontSize: 11 } },
      series: [
        {
          type: 'bar',
          data: flows,
          itemStyle: { color: (p: { value: number }) => (p.value >= 0 ? '#e5484d' : '#2e9e6b') },
          barWidth: 10,
        },
      ],
    });
    return () => chart.dispose();
  }, [data]);
  return <div ref={ref} style={{ width: '100%', height: 260 }} />;
}
