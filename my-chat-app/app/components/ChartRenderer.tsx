'use client';

/**
 * ChartRenderer — renders an ECharts chart from a `VisualizationSpec`.
 *
 * The spec comes from the backend Visualization Planner (an LLM post-processing
 * stage); this component is deliberately dumb: it never decides *which* charts
 * to show, it only turns a given spec into ECharts options.
 */

import { Box, Typography } from '@mui/material';
import * as echarts from 'echarts/core';
import { BarChart, HeatmapChart, LineChart, PieChart, ScatterChart, TreemapChart } from 'echarts/charts';
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { memo, useEffect, useMemo, useRef } from 'react';

echarts.use([
  LineChart,
  BarChart,
  PieChart,
  ScatterChart,
  HeatmapChart,
  TreemapChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  CanvasRenderer,
]);

export const CHART_TYPES = [
  'line',
  'bar',
  'pie',
  'donut',
  'scatter',
  'heatmap',
  'treemap',
] as const;

export type ChartType = (typeof CHART_TYPES)[number];

/** Mirror of `src/models.py::VisualizationSpec`. */
export interface VisualizationSpec {
  chart_type: ChartType;
  title: string;
  description: string;
  x_field: string | null;
  y_field: string | null;
  category_field: string | null;
  value_field: string | null;
  data: Record<string, unknown>[];
}

const PALETTE = [
  '#1976d2',
  '#ff9800',
  '#4caf50',
  '#f44336',
  '#9c27b0',
  '#00bcd4',
  '#8d6e63',
  '#607d8b',
  '#e91e63',
  '#7cb342',
];

function toNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number.parseFloat(value.replace(/[$,%]/g, ''));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function firstNumericField(data: Record<string, unknown>[], exclude: Set<string>): string | null {
  for (const row of data) {
    for (const [key, value] of Object.entries(row)) {
      if (exclude.has(key)) continue;
      if (toNumber(value) !== null) return key;
    }
  }
  return null;
}

/** Build the ECharts option for a given spec. Pure and unit-testable. */
export function buildEChartsOption(spec: VisualizationSpec): echarts.EChartsCoreOption {
  switch (spec.chart_type) {
    case 'line':
    case 'bar':
      return buildAxisOption(spec);
    case 'pie':
    case 'donut':
      return buildPieOption(spec);
    case 'scatter':
      return buildScatterOption(spec);
    case 'heatmap':
      return buildHeatmapOption(spec);
    case 'treemap':
      return buildTreemapOption(spec);
  }
}

function buildAxisOption(spec: VisualizationSpec): echarts.EChartsCoreOption {
  const rows = spec.data;
  const xField =
    spec.x_field ?? firstNumericField(rows, new Set([spec.y_field ?? ''])) ?? '';
  const yField =
    spec.y_field ?? spec.value_field ?? firstNumericField(rows, new Set([xField])) ?? '';

  const xValues = [...new Set(rows.map((row) => String(row[xField] ?? '')))];
  const points = rows
    .map((row) => ({
      x: String(row[xField] ?? ''),
      y: toNumber(row[yField]),
    }))
    .filter((point): point is { x: string; y: number } => point.y !== null);

  const isBar = spec.chart_type === 'bar';
  return {
    color: PALETTE,
    tooltip: { trigger: 'axis' },
    grid: { left: 16, right: 24, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      data: xValues,
      axisLabel: { rotate: xValues.length > 6 ? 30 : 0 },
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: yField ?? undefined,
        type: isBar ? 'bar' : 'line',
        smooth: !isBar,
        symbol: isBar ? 'none' : 'circle',
        itemStyle: isBar ? { borderRadius: [4, 4, 0, 0] } : undefined,
        areaStyle: isBar
          ? undefined
          : { opacity: 0.12 },
        data: points.map((point) => [point.x, point.y]),
      },
    ],
  };
}

function buildPieOption(spec: VisualizationSpec): echarts.EChartsCoreOption {
  const rows = spec.data;
  const nameField =
    spec.category_field ?? spec.x_field ?? firstNumericField(rows, new Set()) ?? '';
  const valueField =
    spec.value_field ?? spec.y_field ?? firstNumericField(rows, new Set([nameField])) ?? '';

  const isDonut = spec.chart_type === 'donut';
  return {
    color: PALETTE,
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, type: 'scroll' },
    series: [
      {
        name: valueField ?? undefined,
        type: 'pie',
        radius: isDonut ? ['42%', '68%'] : '62%',
        center: ['50%', '46%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 1 },
        label: { show: !isDonut, formatter: '{b}' },
        data: rows
          .map((row) => ({
            name: String(row[nameField] ?? ''),
            value: toNumber(row[valueField]),
          }))
          .filter((item): item is { name: string; value: number } => item.value !== null),
      },
    ],
  };
}

function buildScatterOption(spec: VisualizationSpec): echarts.EChartsCoreOption {
  const rows = spec.data;
  const xField = spec.x_field ?? firstNumericField(rows, new Set()) ?? '';
  const yField = spec.y_field ?? firstNumericField(rows, new Set([xField])) ?? '';

  return {
    tooltip: { trigger: 'item' },
    grid: { left: 16, right: 24, top: 16, bottom: 8, containLabel: true },
    xAxis: { type: 'value', name: xField ?? undefined },
    yAxis: { type: 'value', name: yField ?? undefined },
    series: [
      {
        type: 'scatter',
        symbolSize: 11,
        itemStyle: { color: PALETTE[0], opacity: 0.75 },
        data: rows
          .map((row) => [toNumber(row[xField]), toNumber(row[yField])])
          .filter((pair) => pair[0] !== null && pair[1] !== null),
      },
    ],
  };
}

function buildHeatmapOption(spec: VisualizationSpec): echarts.EChartsCoreOption {
  const rows = spec.data;
  const xField = spec.x_field ?? '';
  const yField = spec.y_field ?? '';
  const valueField = spec.value_field ?? firstNumericField(rows, new Set([xField, yField])) ?? '';

  const xValues = [...new Set(rows.map((row) => String(row[xField] ?? '')))];
  const yValues = [...new Set(rows.map((row) => String(row[yField] ?? '')))];
  const xIndex = new Map(xValues.map((value, index) => [value, index]));
  const yIndex = new Map(yValues.map((value, index) => [value, index]));

  const values = rows
    .map((row) => {
      const value = toNumber(row[valueField]);
      if (value === null) return null;
      const x = xIndex.get(String(row[xField] ?? ''));
      const y = yIndex.get(String(row[yField] ?? ''));
      if (x === undefined || y === undefined) return null;
      return [x, y, value];
    })
    .filter((cell): cell is [number, number, number] => cell !== null);

  const numeric = values.map((cell) => cell[2]);
  if (numeric.length === 0) {
    return { series: [{ type: 'heatmap', data: [] }] };
  }
  const min = Math.min(...numeric);
  const max = Math.max(...numeric);

  return {
    tooltip: { position: 'top' },
    grid: { left: 16, right: 24, top: 8, bottom: 8, containLabel: true },
    xAxis: { type: 'category', data: xValues, splitArea: { show: true } },
    yAxis: { type: 'category', data: [...yValues].reverse(), splitArea: { show: true } },
    visualMap: {
      min,
      max,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#e3f2fd', '#1976d2', '#b71c1c'] },
    },
    series: [
      {
        type: 'heatmap',
        data: values,
        label: { show: numeric.length <= 60 },
        emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.4)' } },
      },
    ],
  };
}

function buildTreemapOption(spec: VisualizationSpec): echarts.EChartsCoreOption {
  const rows = spec.data;
  const nameField = spec.category_field ?? spec.x_field ?? '';
  const valueField = spec.value_field ?? spec.y_field ?? firstNumericField(rows, new Set([nameField])) ?? '';

  const toTreeNode = (row: Record<string, unknown>): { name: string; value: number; children?: unknown[] } => {
    const children = Array.isArray(row.children) ? (row.children as Record<string, unknown>[]) : [];
    const node: { name: string; value: number; children?: unknown[] } = {
      name: String(row[nameField] ?? ''),
      value: toNumber(row[valueField]) ?? 0,
    };
    if (children.length > 0) {
      node.children = children.map(toTreeNode);
    }
    return node;
  };

  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c}' },
    series: [
      {
        type: 'treemap',
        roam: false,
        nodeClick: 'zoomToNode',
        breadcrumb: { show: rows.some((row) => Array.isArray(row.children)) },
        label: { show: true, formatter: '{b}' },
        itemStyle: { borderColor: '#fff', borderWidth: 1, gapWidth: 2 },
        data: rows.map(toTreeNode),
      },
    ],
  };
}

function ChartRenderer({ spec }: { spec: VisualizationSpec }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const option = useMemo(() => buildEChartsOption(spec), [spec]);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const chart = echarts.init(element);
    chart.setOption(option);

    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(element);

    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [option]);

  return (
    <Box component="figure" sx={{ m: 0, width: '100%' }}>
      <Typography variant="subtitle2" component="figcaption" sx={{ mb: 0.5 }}>
        {spec.title}
      </Typography>
      <Box ref={containerRef} sx={{ width: '100%', height: 280 }} />
      {spec.description ? (
        <Typography variant="caption" color="text.secondary">
          {spec.description}
        </Typography>
      ) : null}
    </Box>
  );
}

export default memo(ChartRenderer);
