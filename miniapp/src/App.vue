<script>
import {
  API_TRANSPORT,
  CLOUDBASE_ENV_ID,
  validateCloudBaseConfig,
} from './config/runtime'

export default {
  onLaunch() {
    // #ifdef MP-WEIXIN
    if (API_TRANSPORT === 'cloudbase') {
      try {
        validateCloudBaseConfig()
        if (!wx.cloud) throw new Error('当前微信基础库不支持云开发')
        wx.cloud.init({ env: CLOUDBASE_ENV_ID, traceUser: true })
      } catch (error) {
        console.error('CloudBase 初始化失败', error)
        uni.showModal({
          title: '服务配置错误',
          content: error.message || 'CloudBase 初始化失败',
          showCancel: false,
        })
      }
    }
    // #endif
    console.info('食尽其用小程序启动')
  },
}
</script>

<style>
page {
  min-height: 100%;
  background: #f5f7f2;
  color: #243229;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
}

view, text, input, picker, textarea, button {
  box-sizing: border-box;
}

button::after {
  border: none;
}

.page {
  min-height: 100vh;
  padding: 28rpx 28rpx 48rpx;
}

.card {
  background: #ffffff;
  border-radius: 24rpx;
  padding: 28rpx;
  box-shadow: 0 8rpx 30rpx rgba(44, 91, 59, 0.07);
}

.primary-button {
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 44rpx;
  background: #2f7d4a;
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}

.secondary-button {
  height: 76rpx;
  line-height: 76rpx;
  border-radius: 38rpx;
  background: #e8f3eb;
  color: #2f7d4a;
  font-size: 28rpx;
}

.muted {
  color: #859088;
}

.empty {
  padding: 90rpx 20rpx;
  text-align: center;
  color: #909a93;
}
</style>
