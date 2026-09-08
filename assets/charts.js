(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var accent3 = style.getPropertyValue('--accent3').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();
  var success = style.getPropertyValue('--success').trim();
  var danger = style.getPropertyValue('--danger').trim();

  // --- Chart: Top 10 Retail Inflow (Horizontal Bar) ---
  var chart1 = echarts.init(document.getElementById('chart-top10'), null, { renderer: 'svg' });

  var top10Data = [
    { name: '中国船舶', value: 9.12, change: 2.43 },
    { name: '中国平安', value: 4.78, change: -3.23 },
    { name: '宏和科技', value: 4.68, change: 2.59 },
    { name: '天娱数科', value: 4.67, change: -0.24 },
    { name: '宁德时代', value: 4.52, change: -0.80 },
    { name: '长江电力', value: 3.65, change: -2.01 },
    { name: '东方财富', value: 3.07, change: -0.84 },
    { name: '浪潮信息', value: 3.02, change: -3.83 },
    { name: '白银有色', value: 2.97, change: -4.11 },
    { name: '德福科技', value: 2.76, change: 16.97 }
  ];

  // Reverse for horizontal bar (top to bottom)
  top10Data.reverse();

  chart1.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      appendToBody: true,
      backgroundColor: bg2,
      borderColor: rule,
      textStyle: { color: ink },
      formatter: function(params) {
        var d = params[0];
        var item = top10Data[d.dataIndex];
        var changeColor = item.change >= 0 ? success : danger;
        var changeSign = item.change >= 0 ? '+' : '';
        return '<div style="font-weight:600;margin-bottom:4px;">' + d.name + '</div>' +
               '<div>散户净流入：<span style="color:' + success + ';font-weight:600;">' + d.value.toFixed(2) + ' 亿元</span></div>' +
               '<div>当日涨跌：<span style="color:' + changeColor + ';font-weight:600;">' + changeSign + item.change.toFixed(2) + '%</span></div>';
      }
    },
    grid: {
      left: '3%',
      right: '8%',
      bottom: '3%',
      top: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: muted,
        fontSize: 11,
        formatter: '{value}亿'
      },
      splitLine: {
        lineStyle: {
          color: rule,
          type: 'dashed'
        }
      }
    },
    yAxis: {
      type: 'category',
      data: top10Data.map(function(d) { return d.name; }),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: ink,
        fontSize: 12,
        fontWeight: 500
      }
    },
    series: [{
      type: 'bar',
      data: top10Data.map(function(d, i) {
        return {
          value: d.value,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: i >= 7 ? accent : accent2 + '99' },
              { offset: 1, color: i >= 7 ? accent + '66' : accent2 + '44' }
            ]),
            borderRadius: [0, 4, 4, 0]
          }
        };
      }),
      barWidth: 18,
      label: {
        show: true,
        position: 'right',
        color: ink,
        fontSize: 12,
        fontWeight: 600,
        formatter: '{c}亿'
      }
    }]
  });

  // --- Chart: Sector Radar ---
  var chart2 = echarts.init(document.getElementById('chart-radar'), null, { renderer: 'svg' });

  chart2.setOption({
    animation: false,
    tooltip: {
      trigger: 'item',
      appendToBody: true,
      backgroundColor: bg2,
      borderColor: rule,
      textStyle: { color: ink }
    },
    radar: {
      indicator: [
        { name: 'PCB/算力', max: 100 },
        { name: '农业种植', max: 100 },
        { name: '零售消费', max: 100 },
        { name: '新能源', max: 100 },
        { name: '金融保险', max: 100 },
        { name: '医药生物', max: 100 }
      ],
      center: ['50%', '50%'],
      radius: '65%',
      axisName: {
        color: ink,
        fontSize: 12,
        fontWeight: 500
      },
      splitLine: {
        lineStyle: {
          color: rule
        }
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: [bg2, bg2 + 'aa']
        }
      },
      axisLine: {
        lineStyle: {
          color: rule
        }
      }
    },
    series: [{
      type: 'radar',
      data: [
        {
          value: [95, 75, 65, 55, 50, 45],
          name: '散户资金热度',
          areaStyle: {
            color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
              { offset: 0, color: accent + '44' },
              { offset: 1, color: accent + '11' }
            ])
          },
          lineStyle: {
            color: accent,
            width: 2
          },
          itemStyle: {
            color: accent,
            borderColor: bg2,
            borderWidth: 2
          },
          symbol: 'circle',
          symbolSize: 6
        }
      ]
    }]
  });

  // --- Chart: Quarterly Absolute Increase (Horizontal Bar) ---
  var chart3 = echarts.init(document.getElementById('chart-quarterly-abs'), null, { renderer: 'svg' });

  var quarterlyAbsData = [
    { name: '比亚迪', value: 3.64 },
    { name: '中际旭创', value: 5.13 },
    { name: '兆易创新', value: 11.65 },
    { name: '华工科技', value: 15 },
    { name: '生益科技', value: 18 },
    { name: '亨通光电', value: 25 },
    { name: '华天科技', value: 35 },
    { name: '长电科技', value: 50 },
    { name: '中天科技', value: 59.19 },
    { name: '京东方A', value: 92.56 }
  ];

  chart3.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      appendToBody: true,
      backgroundColor: bg2,
      borderColor: rule,
      textStyle: { color: ink },
      formatter: function(params) {
        var d = params[0];
        return '<div style="font-weight:600;margin-bottom:4px;">' + d.name + '</div>' +
               '<div>新增股东：<span style="color:' + success + ';font-weight:600;">' + d.value.toFixed(2) + ' 万户</span></div>';
      }
    },
    grid: {
      left: '3%',
      right: '10%',
      bottom: '3%',
      top: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: muted,
        fontSize: 10,
        formatter: '{value}万'
      },
      splitLine: {
        lineStyle: {
          color: rule,
          type: 'dashed'
        }
      }
    },
    yAxis: {
      type: 'category',
      data: quarterlyAbsData.map(function(d) { return d.name; }),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: ink,
        fontSize: 11,
        fontWeight: 500
      }
    },
    series: [{
      type: 'bar',
      data: quarterlyAbsData.map(function(d, i) {
        return {
          value: d.value,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: i >= 7 ? accent : accent2 + '88' },
              { offset: 1, color: i >= 7 ? accent + '55' : accent2 + '33' }
            ]),
            borderRadius: [0, 4, 4, 0]
          }
        };
      }),
      barWidth: 14,
      label: {
        show: true,
        position: 'right',
        color: ink,
        fontSize: 11,
        fontWeight: 600,
        formatter: '{c}万'
      }
    }]
  });

  // --- Chart: Quarterly Growth Rate (Horizontal Bar) ---
  var chart4 = echarts.init(document.getElementById('chart-quarterly-rate'), null, { renderer: 'svg' });

  var quarterlyRateData = [
    { name: '京东方A', value: 95.23 },
    { name: '长电科技', value: 164.54 },
    { name: '中国巨石', value: 250 },
    { name: '凯盛科技', value: 250 },
    { name: '圣泉集团', value: 250 },
    { name: '沃格光电', value: 250 },
    { name: '彩虹股份', value: 278.83 },
    { name: '中天科技', value: 261.64 },
    { name: '快克智能', value: 335.83 },
    { name: '昊华科技', value: 457.26 }
  ];

  chart4.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      appendToBody: true,
      backgroundColor: bg2,
      borderColor: rule,
      textStyle: { color: ink },
      formatter: function(params) {
        var d = params[0];
        return '<div style="font-weight:600;margin-bottom:4px;">' + d.name + '</div>' +
               '<div>单季增幅：<span style="color:' + accent3 + ';font-weight:600;">+' + d.value.toFixed(2) + '%</span></div>';
      }
    },
    grid: {
      left: '3%',
      right: '10%',
      bottom: '3%',
      top: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: muted,
        fontSize: 10,
        formatter: '{value}%'
      },
      splitLine: {
        lineStyle: {
          color: rule,
          type: 'dashed'
        }
      }
    },
    yAxis: {
      type: 'category',
      data: quarterlyRateData.map(function(d) { return d.name; }),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: ink,
        fontSize: 11,
        fontWeight: 500
      }
    },
    series: [{
      type: 'bar',
      data: quarterlyRateData.map(function(d, i) {
        return {
          value: d.value,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: i >= 7 ? accent3 : danger + '99' },
              { offset: 1, color: i >= 7 ? accent3 + '55' : danger + '33' }
            ]),
            borderRadius: [0, 4, 4, 0]
          }
        };
      }),
      barWidth: 14,
      label: {
        show: true,
        position: 'right',
        color: ink,
        fontSize: 11,
        fontWeight: 600,
        formatter: '+{c}%'
      }
    }]
  });

  // Resize listeners
  window.addEventListener('resize', function() {
    chart1.resize();
    chart2.resize();
    chart3.resize();
    chart4.resize();
  });
})();
