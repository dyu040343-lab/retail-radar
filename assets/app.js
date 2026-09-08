// 散户雷达侦探 - 动态数据加载与渲染
(function() {
  'use strict';

  // 全局状态
  var radarData = null;
  var autoRefreshTimer = null;
  var autoRefreshEnabled = false;

  // CSS变量缓存
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var accent3 = style.getPropertyValue('--accent3').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();
  var bg3 = style.getPropertyValue('--bg3').trim();
  var success = style.getPropertyValue('--success').trim();
  var danger = style.getPropertyValue('--danger').trim();

  // 图表实例
  var chartTopInflow = null;
  var chartCountAbs = null;
  var chartCountRate = null;

  // 板块标签映射
  var sectorTags = {
    '半导体': 'tag-pcb', '芯片': 'tag-pcb', 'PCB': 'tag-pcb', '光模块': 'tag-pcb',
    '算力': 'tag-pcb', '存储': 'tag-pcb', '面板': 'tag-pcb', '通信': 'tag-pcb',
    '新能源': 'tag-new', '锂电': 'tag-new', '光伏': 'tag-new', '汽车': 'tag-new',
    '医药': 'tag-hot', '医疗': 'tag-hot',
    '金融': 'tag-fin', '银行': 'tag-fin', '证券': 'tag-fin', '保险': 'tag-fin',
    '农业': 'tag-agri', '食品': 'tag-agri', '消费': 'tag-agri'
  };

  function getSectorTag(name, code) {
    for (var key in sectorTags) {
      if (name.indexOf(key) !== -1) return sectorTags[key];
    }
    // 根据代码简单判断
    if (code && (code.startsWith('601') || code.startsWith('6000') || code.startsWith('6013'))) return 'tag-fin';
    if (code && code.startsWith('300')) return 'tag-pcb';
    return 'tag-new';
  }

  // 加载数据
  function loadData() {
    return fetch('data/radar_data.json?_t=' + Date.now())
      .then(function(res) {
        if (!res.ok) throw new Error('数据加载失败');
        return res.json();
      });
  }

  // 渲染概览数据
  function renderOverview(data) {
    var overview = data.overview || {};
    var retail = data.retail_money_flow || [];
    var count = data.shareholder_count || [];

    // 更新时间
    document.getElementById('updateTime').textContent = '更新时间: ' + (data.last_updated || '--');

    // 数据状态提示
    var liveStatus = document.getElementById('liveStatus');
    if (data.data_status === 'live') {
      liveStatus.textContent = '实时数据';
      liveStatus.parentElement.style.borderColor = 'var(--accent)';
    } else {
      liveStatus.textContent = '静态数据';
      liveStatus.parentElement.style.borderColor = 'var(--accent3)';
      liveStatus.parentElement.style.color = 'var(--accent3)';
    }

    // 资金概览
    if (retail.length > 0) {
      var top = retail[0];
      document.getElementById('topInflowStock').textContent = top.name || '--';
      document.getElementById('topInflowAmount').textContent = '+' + (top.retail_net_inflow || 0).toFixed(2) + '亿';

      var positiveCount = retail.filter(function(s) { return s.retail_net_inflow > 0; }).length;
      document.getElementById('retailStocksCount').textContent = positiveCount + '只';

      var totalInflow = retail.reduce(function(sum, s) {
        return sum + (s.retail_net_inflow > 0 ? s.retail_net_inflow : 0);
      }, 0);
      document.getElementById('totalRetailInflow').textContent = totalInflow.toFixed(0) + '亿';
    }

    // 户数概览
    if (count.length > 0) {
      var sortedByInc = count.slice().sort(function(a, b) { return b.increase - a.increase; });
      var sortedByRate = count.slice().sort(function(a, b) { return b.change_pct - a.change_pct; });

      var topInc = sortedByInc[0];
      var topRate = sortedByRate[0];

      document.getElementById('topIncreaseName').textContent = topInc.name || '--';
      document.getElementById('topIncreaseAmount').textContent =
        '+' + formatNumber(topInc.increase) + '户';

      document.getElementById('topRateName').textContent = topRate.name || '--';
      document.getElementById('topRateAmount').textContent = '+' + topRate.change_pct.toFixed(2) + '%';

      document.getElementById('monitoredCount').textContent = count.length + '只';
    }
  }

  // 格式化数字
  function formatNumber(num) {
    if (num >= 10000) return (num / 10000).toFixed(2) + '万';
    return num.toLocaleString();
  }

  // 渲染资金流向表格
  function renderMoneyTable(data) {
    var tbody = document.getElementById('moneyTableBody');
    var stocks = data.retail_money_flow || [];

    if (stocks.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:2rem;">暂无数据</td></tr>';
      return;
    }

    var html = '';
    stocks.forEach(function(stock, i) {
      var rankClass = i < 3 ? 'rank-' + (i + 1) : 'rank-other';
      var changeClass = stock.change_pct >= 0 ? 'positive' : 'negative';
      var inflowClass = stock.retail_net_inflow >= 0 ? 'positive' : 'negative';
      var mainClass = stock.main_net >= 0 ? 'positive' : 'negative';
      var changeSign = stock.change_pct >= 0 ? '+' : '';
      var inflowSign = stock.retail_net_inflow >= 0 ? '+' : '';
      var mainSign = stock.main_net >= 0 ? '+' : '';
      var tagClass = getSectorTag(stock.name, stock.code);

      html += '<tr>' +
        '<td><span class="rank-badge ' + rankClass + '">' + (i + 1) + '</span></td>' +
        '<td><span class="stock-name">' + stock.name + '</span><span class="stock-code">' + stock.code + '</span></td>' +
        '<td class="amount">' + stock.price.toFixed(2) + '</td>' +
        '<td class="amount ' + changeClass + '">' + changeSign + stock.change_pct.toFixed(2) + '%</td>' +
        '<td class="amount ' + inflowClass + '">' + inflowSign + stock.retail_net_inflow.toFixed(2) + '</td>' +
        '<td class="amount ' + mainClass + '">' + mainSign + stock.main_net.toFixed(2) + '</td>' +
        '<td><span class="tag ' + tagClass + '">' + (stock.sector || '--') + '</span></td>' +
      '</tr>';
    });
    tbody.innerHTML = html;
  }

  // 渲染股东户数表格
  function renderCountTable(data) {
    var tbody = document.getElementById('countTableBody');
    var stocks = data.shareholder_count || [];

    if (stocks.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:2rem;">暂无数据</td></tr>';
      return;
    }

    var html = '';
    stocks.forEach(function(stock, i) {
      var rankClass = i < 3 ? 'rank-' + (i + 1) : 'rank-other';
      var incClass = stock.change_pct >= 0 ? 'positive' : 'negative';
      var incSign = stock.change_pct >= 0 ? '+' : '';
      var incNumSign = stock.increase >= 0 ? '+' : '';
      var tagClass = getSectorTag(stock.name, stock.code);

      html += '<tr>' +
        '<td><span class="rank-badge ' + rankClass + '">' + (i + 1) + '</span></td>' +
        '<td><span class="stock-name">' + stock.name + '</span><span class="stock-code">' + stock.code + '</span></td>' +
        '<td class="amount">' + formatNumber(stock.current) + '</td>' +
        '<td class="amount ' + incClass + '">' + incNumSign + formatNumber(stock.increase) + '</td>' +
        '<td class="amount ' + incClass + '">' + incSign + stock.change_pct.toFixed(2) + '%</td>' +
        '<td style="color:var(--muted);font-size:0.8rem;">' + (stock.period || '--') + '</td>' +
        '<td><span class="tag ' + tagClass + '">' + (stock.sector || '--') + '</span></td>' +
      '</tr>';
    });
    tbody.innerHTML = html;
  }

  // 渲染散户净流入TOP20图表
  function renderTopInflowChart(data) {
    if (!chartTopInflow) {
      chartTopInflow = echarts.init(document.getElementById('chart-topinflow'), null, { renderer: 'svg' });
    }

    var stocks = (data.retail_money_flow || []).slice(0, 20).reverse();

    chartTopInflow.setOption({
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
          var item = stocks[d.dataIndex];
          var changeColor = item.change_pct >= 0 ? success : danger;
          var changeSign = item.change_pct >= 0 ? '+' : '';
          return '<div style="font-weight:600;margin-bottom:4px;">' + item.name + ' (' + item.code + ')</div>' +
                 '<div>散户净流入：<span style="color:' + success + ';font-weight:600;">' + item.retail_net_inflow.toFixed(2) + ' 亿元</span></div>' +
                 '<div>主力净额：<span style="color:' + (item.main_net >= 0 ? success : danger) + ';font-weight:600;">' + (item.main_net >= 0 ? '+' : '') + item.main_net.toFixed(2) + ' 亿元</span></div>' +
                 '<div>涨跌幅：<span style="color:' + changeColor + ';font-weight:600;">' + changeSign + item.change_pct.toFixed(2) + '%</span></div>';
        }
      },
      grid: { left: '3%', right: '6%', bottom: '3%', top: '3%', containLabel: true },
      xAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: muted, fontSize: 11, formatter: '{value}亿' },
        splitLine: { lineStyle: { color: rule, type: 'dashed' } }
      },
      yAxis: {
        type: 'category',
        data: stocks.map(function(d) { return d.name; }),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: ink, fontSize: 11, fontWeight: 500 }
      },
      series: [{
        type: 'bar',
        data: stocks.map(function(d, i) {
          var isTop = i >= stocks.length - 3;
          var isPositive = d.retail_net_inflow >= 0;
          return {
            value: d.retail_net_inflow,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: isTop ? (isPositive ? accent : danger) : accent2 + '88' },
                { offset: 1, color: isTop ? (isPositive ? accent + '66' : danger + '66') : accent2 + '44' }
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
          formatter: function(p) { return (p.value >= 0 ? '+' : '') + p.value.toFixed(2) + '亿'; }
        }
      }]
    });
  }

  // 渲染股东户数增量图表
  function renderCountAbsChart(data) {
    if (!chartCountAbs) {
      chartCountAbs = echarts.init(document.getElementById('chart-count-abs'), null, { renderer: 'svg' });
    }

    var stocks = (data.shareholder_count || [])
      .slice()
      .sort(function(a, b) { return a.increase - b.increase; })
      .slice(-10);

    chartCountAbs.setOption({
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
          var item = stocks[d.dataIndex];
          return '<div style="font-weight:600;margin-bottom:4px;">' + item.name + '</div>' +
                 '<div>新增户数：<span style="color:' + success + ';font-weight:600;">' + formatNumber(item.increase) + '</span></div>' +
                 '<div>最新户数：' + formatNumber(item.current) + '</div>';
        }
      },
      grid: { left: '3%', right: '10%', bottom: '3%', top: '3%', containLabel: true },
      xAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: muted, fontSize: 10, formatter: function(v) { return (v/10000).toFixed(0) + '万'; } },
        splitLine: { lineStyle: { color: rule, type: 'dashed' } }
      },
      yAxis: {
        type: 'category',
        data: stocks.map(function(d) { return d.name; }),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: ink, fontSize: 11, fontWeight: 500 }
      },
      series: [{
        type: 'bar',
        data: stocks.map(function(d, i) {
          var isTop = i >= stocks.length - 3;
          return {
            value: d.increase,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: isTop ? accent : accent2 + '88' },
                { offset: 1, color: isTop ? accent + '55' : accent2 + '33' }
              ]),
              borderRadius: [0, 4, 4, 0]
            }
          };
        }),
        barWidth: 12,
        label: {
          show: true,
          position: 'right',
          color: ink,
          fontSize: 10,
          fontWeight: 600,
          formatter: function(p) {
            var v = p.value;
            if (v >= 10000) return '+' + (v/10000).toFixed(1) + '万';
            return '+' + v;
          }
        }
      }]
    });
  }

  // 渲染股东户数增幅图表
  function renderCountRateChart(data) {
    if (!chartCountRate) {
      chartCountRate = echarts.init(document.getElementById('chart-count-rate'), null, { renderer: 'svg' });
    }

    var stocks = (data.shareholder_count || [])
      .slice()
      .sort(function(a, b) { return a.change_pct - b.change_pct; })
      .slice(-10);

    chartCountRate.setOption({
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
          var item = stocks[d.dataIndex];
          return '<div style="font-weight:600;margin-bottom:4px;">' + item.name + '</div>' +
                 '<div>增幅：<span style="color:' + accent3 + ';font-weight:600;">+' + item.change_pct.toFixed(2) + '%</span></div>' +
                 '<div>行业：' + (item.sector || '--') + '</div>';
        }
      },
      grid: { left: '3%', right: '12%', bottom: '3%', top: '3%', containLabel: true },
      xAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: muted, fontSize: 10, formatter: '{value}%' },
        splitLine: { lineStyle: { color: rule, type: 'dashed' } }
      },
      yAxis: {
        type: 'category',
        data: stocks.map(function(d) { return d.name; }),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: ink, fontSize: 11, fontWeight: 500 }
      },
      series: [{
        type: 'bar',
        data: stocks.map(function(d, i) {
          var isTop = i >= stocks.length - 3;
          return {
            value: d.change_pct,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: isTop ? accent3 : danger + '88' },
                { offset: 1, color: isTop ? accent3 + '55' : danger + '33' }
              ]),
              borderRadius: [0, 4, 4, 0]
            }
          };
        }),
        barWidth: 12,
        label: {
          show: true,
          position: 'right',
          color: ink,
          fontSize: 10,
          fontWeight: 600,
          formatter: '+{c}%'
        }
      }]
    });
  }

  // 完整渲染
  function renderAll(data) {
    radarData = data;
    renderOverview(data);
    renderMoneyTable(data);
    renderCountTable(data);
    renderTopInflowChart(data);
    renderCountAbsChart(data);
    renderCountRateChart(data);
  }

  // 刷新数据
  function refreshData() {
    var btn = document.getElementById('refreshBtn');
    btn.classList.add('loading');
    btn.innerHTML = '<span class="spin">🔄</span> 刷新中...';

    loadData()
      .then(function(data) {
        renderAll(data);
        btn.classList.remove('loading');
        btn.innerHTML = '<span>🔄</span> 手动刷新';
      })
      .catch(function(err) {
        console.error('刷新失败:', err);
        btn.classList.remove('loading');
        btn.innerHTML = '<span>⚠️</span> 刷新失败';
        setTimeout(function() {
          btn.innerHTML = '<span>🔄</span> 手动刷新';
        }, 2000);
      });
  }

  // Tab切换
  function switchTab(tabId) {
    // 更新按钮状态
    document.querySelectorAll('.tab-btn').forEach(function(btn) {
      btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    // 更新面板
    document.querySelectorAll('.tab-panel').forEach(function(panel) {
      panel.classList.toggle('active', panel.id === tabId);
    });
    // 调整图表大小
    setTimeout(function() {
      if (chartTopInflow) chartTopInflow.resize();
      if (chartCountAbs) chartCountAbs.resize();
      if (chartCountRate) chartCountRate.resize();
    }, 50);
  }

  // 表格排序
  function sortTable(tableId, colIndex) {
    var table = document.getElementById(tableId);
    var tbody = table.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr'));
    var ths = table.querySelectorAll('th');

    // 切换排序方向
    var currentSorted = table.querySelector('th.sorted');
    var ascending = true;
    if (currentSorted && currentSorted === ths[colIndex]) {
      ascending = !currentSorted.dataset.asc || currentSorted.dataset.asc === 'false';
    }

    // 移除所有排序标记
    ths.forEach(function(th) {
      th.classList.remove('sorted');
      delete th.dataset.asc;
    });
    ths[colIndex].classList.add('sorted');
    ths[colIndex].dataset.asc = ascending;

    // 排序
    rows.sort(function(a, b) {
      var aVal = a.cells[colIndex].textContent.trim();
      var bVal = b.cells[colIndex].textContent.trim();
      // 尝试数字比较
      var aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
      var bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));
      if (!isNaN(aNum) && !isNaN(bNum)) {
        return ascending ? aNum - bNum : bNum - aNum;
      }
      return ascending ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });

    // 重新排名（第一列）
    if (colIndex === 0) {
      rows.forEach(function(row, i) {
        var rankClass = i < 3 ? 'rank-' + (i + 1) : 'rank-other';
        var badge = row.querySelector('.rank-badge');
        if (badge) {
          badge.className = 'rank-badge ' + rankClass;
          badge.textContent = i + 1;
        }
      });
    }

    // 重新插入
    rows.forEach(function(row) {
      tbody.appendChild(row);
    });
  }

  // 自动刷新
  function toggleAutoRefresh() {
    var toggle = document.getElementById('autoRefreshToggle');
    autoRefreshEnabled = !autoRefreshEnabled;
    toggle.classList.toggle('active', autoRefreshEnabled);

    if (autoRefreshEnabled) {
      autoRefreshTimer = setInterval(refreshData, 60000);
    } else {
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
      }
    }
  }

  // 窗口大小变化
  window.addEventListener('resize', function() {
    if (chartTopInflow) chartTopInflow.resize();
    if (chartCountAbs) chartCountAbs.resize();
    if (chartCountRate) chartCountRate.resize();
  });

  // 暴露全局函数
  window.refreshData = refreshData;
  window.switchTab = switchTab;
  window.sortTable = sortTable;
  window.toggleAutoRefresh = toggleAutoRefresh;

  // 初始化
  document.addEventListener('DOMContentLoaded', function() {
    loadData()
      .then(function(data) {
        renderAll(data);
        // 隐藏加载遮罩
        setTimeout(function() {
          document.getElementById('loadingOverlay').classList.add('hidden');
        }, 500);
      })
      .catch(function(err) {
        console.error('数据加载失败:', err);
        document.getElementById('loadingOverlay').innerHTML =
          '<div style="color:var(--danger);font-size:1rem;">数据加载失败</div>' +
          '<div style="color:var(--muted);font-size:0.8rem;margin-top:0.5rem;">请稍后刷新重试</div>';
      });
  });
})();
