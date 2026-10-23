Component({
  data: {
    selected: 0,
    hidden: false,
    list: [
      { pagePath: '/pages/index/index', text: '首页' },
      { pagePath: '/pages/school/school', text: '学校' },
    ],
  },
  methods: {
    switchTab(e) {
      const { path, index } = e.currentTarget.dataset;
      wx.switchTab({ url: path });
      this.setData({ selected: index, hidden: false });
    },
  },
});
