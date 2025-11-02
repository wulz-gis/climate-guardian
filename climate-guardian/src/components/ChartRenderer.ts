import * as echarts from 'echarts'

export function renderChart(
  container: HTMLElement,
  type: string,
  _src: string
): void {
  const chart = echarts.init(container)

  if (type === 'heatmap') {
    const hours = ['08:00', '09:00', '10:00', '11:00', '12:00']
    const places = ['操场', '树荫', '楼顶', '教室']
    const data: Array<[number, number, number]> = []
    for (let i = 0; i < places.length; i++) {
      for (let j = 0; j < hours.length; j++) {
        data.push([j, i, Math.round(20 + Math.random() * 8)])
      }
    }
    const option: echarts.EChartsOption = {
      title: { text: '校园不同位置气温对比（℃）', left: 'center' },
      tooltip: { position: 'top' },
      grid: { height: '60%', top: '10%' },
      xAxis: { type: 'category', data: hours, splitArea: { show: true } },
      yAxis: { type: 'category', data: places, splitArea: { show: true } },
      visualMap: {
        min: 18,
        max: 30,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '5%',
        inRange: { color: ['#e0f3f8', '#4575b4', '#d73027'] }
      },
      series: [
        { name: '气温', type: 'heatmap', data, label: { show: true } }
      ]
    }
    chart.setOption(option)
  } else {
    // line / bar 默认示例
    const option: echarts.EChartsOption = {
      xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月'] },
      yAxis: { type: 'value' },
      series: [
        { data: [20, 22, 25, 27, 23, 24], type: type === 'line' ? 'line' : 'bar' }
      ]
    }
    chart.setOption(option)
  }

  window.addEventListener('resize', () => chart.resize())
}