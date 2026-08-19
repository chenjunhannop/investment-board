import * as echarts from 'echarts';
import { useEffect, useRef } from 'react';
import type { SectorRow } from '../api/client';

export default function FundFlowChart({ data }: { data: SectorRow[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    // 前 8 条，条形加宽、带分割线，视觉更紧凑
    const rows = data.slice(0, 8);
    const names = rows.map((d) => d.name);
    const flows = rows.map((d) => d.fund_flow / 1e8); // 亿
    chart.setOption({
      grid: { left: 70, right: 60, top: 10, bottom: 20 },
      tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${v.toFixed(2)} 亿` },
      xAxis: { type: 'value', show: false },
      yAxis: {
        type: 'category',
        data: names,
        axisLabel: { color: '#7c8b9c', fontSize: 12 },
        splitLine: { show: true, lineStyle: { color: 'rgba(124,139,156,0.12)' } },
      },
      series: [
        {
          type: 'bar',
          data: flows,
          label: {
            show: true,
            position: 'right',
            formatter: (p: { value: number }) => `${p.value.toFixed(1)}亿`,
            color: '#7c8b9c',
            fontSize: 12,
          },
          itemStyle: {
            color: (p: { value: number }) => (p.value >= 0 ? '#e5484d' : '#2e9e6b'),
            borderRadius: 3,
          },
          barWidth: 16,
        },
      ],
    });
    return () => chart.dispose();
  }, [data]);
  return <div ref={ref} style={{ width: '100%', height: '100%' }} />;
}
