import * as echarts from 'echarts';
import { useEffect, useRef } from 'react';

interface Props {
  points: number[];
  color: string;
}

export default function IndexMiniChart({ points, color }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  // init 只做一次；数据按内容变化时才 setOption 更新，避免高频重渲染导致闪烁
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    return () => chart.dispose();
  }, []);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const chart = echarts.getInstanceByDom(el);
    if (!chart) return;
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
        },
      ],
    });
  }, [JSON.stringify(points), color]);
  return <div ref={ref} style={{ width: '100%', height: 40 }} />;
}
