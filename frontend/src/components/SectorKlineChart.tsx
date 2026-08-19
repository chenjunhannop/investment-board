import * as echarts from 'echarts';
import { useEffect, useRef } from 'react';

interface Props {
  name: string;
  klines: Array<Array<string | number>>;
  up: boolean;
}

export default function SectorKlineChart({ name, klines, up }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const dates = klines.map((k) => k[0] as string);
    const values = klines.map((k) => [Number(k[1]), Number(k[2]), Number(k[3]), Number(k[4])]);
    const vols = klines.map((k) => Number(k[5]));
    const color = up ? '#e5484d' : '#2e9e6b';
    chart.setOption({
      grid: { left: 44, right: 10, top: 10, bottom: 24 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: dates, show: false },
      yAxis: [
        { type: 'value', scale: true, show: false },
        { type: 'value', show: false },
      ],
      series: [
        {
          type: 'candlestick',
          data: values,
          itemStyle: { color, color0: color, borderColor: color, borderColor0: color },
        },
        {
          type: 'bar',
          yAxisIndex: 1,
          data: vols,
          itemStyle: { color: 'rgba(124,139,156,0.4)' },
        },
      ],
    });
    return () => chart.dispose();
  }, [klines, up, name]);
  return <div ref={ref} style={{ width: '100%', height: '100%' }} />;
}
